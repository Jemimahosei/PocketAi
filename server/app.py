"""
server/app.py — Flask backend for PocketAI web UI

Exposes a /chat endpoint that streams responses from the agentic loop
back to the React frontend using Server-Sent Events (SSE).

Two model backends live behind the same endpoint and the same SSE
contract:

- "llama"  — Llama 3.2 on a local Ollama server (see ollama_backend.py).
             Free, private, no API key. This is the default.
- "claude" — Claude via the Anthropic API, exactly as before. Needs
             ANTHROPIC_API_KEY (config.py or the environment).

The frontend picks the backend per chat (the install-tab choice stored
as `pocketai-model` in the browser, sent as "model" in the /chat
body). Requests without a "model" field use the server default.
"""

import sys
import os
import json

# Add the project root to Python's path so we can import config.py and
# config_manager.py. This is needed because server/app.py is in a
# subdirectory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, Response, send_from_directory, stream_with_context
from flask_cors import CORS

from config_manager import get_agent_name
from tools.file_tool import read_file, list_directory
from tools.pdf_tool import read_pdf
from tools.search_tool import search_web

from ollama_backend import ollama_available, run_llama_chat

# ── Configuration ────────────────────────────────────────────────────────────
#
# Settings come from config.py when it exists (the original setup),
# with environment variables as overrides / fallbacks, so a Llama-only
# install works with no config.py and no Anthropic key at all.

try:
    import config as _config
except ImportError:  # config.py is gitignored and user-created
    _config = None


def _setting(name: str, env_name: str, default=None):
    """config.py attribute first, then environment, then default."""
    if _config is not None and hasattr(_config, name):
        return getattr(_config, name)
    return os.environ.get(env_name, default)


ANTHROPIC_API_KEY = _setting("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
MODEL = _setting("MODEL", "ANTHROPIC_MODEL")
MAX_TOKENS = int(_setting("MAX_TOKENS", "MAX_TOKENS", 1024))
_config_agent_name = _setting("AGENT_NAME", "AGENT_NAME", "PocketAI")

# Llama / Ollama settings.
OLLAMA_HOST = _setting("OLLAMA_HOST", "OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = _setting("OLLAMA_MODEL", "OLLAMA_MODEL", "llama3.2")

# Which backend serves requests that don't name one. PocketAI's free,
# local path is the product default; set POCKETAI_BACKEND=claude (or
# DEFAULT_BACKEND in config.py) to flip the server default.
DEFAULT_BACKEND = str(
    _setting("DEFAULT_BACKEND", "POCKETAI_BACKEND", "llama")
).lower()
if DEFAULT_BACKEND not in ("llama", "claude"):
    DEFAULT_BACKEND = "llama"

app = Flask(__name__)
CORS(app)  # Allow React dev server (port 5173) to talk to Flask (port 5001)

AGENT_NAME = get_agent_name(fallback=_config_agent_name)

SYSTEM_PROMPT = (
    f"You are {AGENT_NAME}, a helpful AI assistant running locally on the user's Mac. When asked about files, look in ~/Downloads, ~/Desktop, ~/Documents, and ~ by default. Use read_pdf for .pdf files, read_file for text files, list_directory to explore folders. "
    "Be concise and direct. Use markdown formatting."
)

# ── Claude client (lazy) ─────────────────────────────────────────────────────
#
# The Anthropic client is built on first use, not at import time, so
# the server starts happily on a Llama-only machine with no key.

_claude_client = None


def get_claude_client():
    """Returns an Anthropic client, or None if Claude isn't configured."""
    global _claude_client
    if _claude_client is None:
        if not ANTHROPIC_API_KEY or not MODEL:
            return None
        try:
            from anthropic import Anthropic
            _claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        except Exception:
            # A client that cannot even be constructed (bad env,
            # proxy or SDK surprise) means "Claude not configured"
            # for routing purposes — callers answer with the honest
            # 503 instead of a 500.
            return None
    return _claude_client


# ── Tool definitions (same as agent.py) ──────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the local filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List all files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list.", "default": "."}
            },
            "required": []
        }
    },
    {
        "name": "read_pdf",
        "description": "Read the text contents of a PDF file from the local filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the PDF file to read."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web using DuckDuckGo and return relevant results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"]
        }
    }
]

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "search_web": search_web,
    "read_pdf": read_pdf,
}

# ── SSE helper ────────────────────────────────────────────────────────────────

def sse_event(event: str, data: dict) -> str:
    """
    Formats a Server-Sent Event string.
    SSE is a simple protocol: each event is 'event: name\ndata: json\n\n'
    The browser's EventSource API parses this automatically.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

# ── Backend selection ─────────────────────────────────────────────────────────

def select_backend(body: dict) -> str:
    """
    The frontend sends {"model": "llama" | "claude"} — the choice from
    its install tabs. Anything else (or nothing) uses the server
    default.
    """
    choice = str(body.get("model", "")).lower()
    return choice if choice in ("llama", "claude") else DEFAULT_BACKEND

# ── Claude loop (unchanged behaviour, extracted) ──────────────────────────────

def generate_claude(conversation_history: list, user_message: str):
    client = get_claude_client()
    history = conversation_history + [{"role": "user", "content": user_message}]

    while True:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=history,
            )
        except Exception as e:
            # Clean message for the UI — never leak a stack trace.
            yield sse_event("error", {"message": f"Claude could not answer: {e}"})
            return

        if response.stop_reason == "end_turn":
            # Stream the response text token by token (word by word for effect)
            full_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    words = block.text.split(" ")
                    for i, word in enumerate(words):
                        chunk = word if i == 0 else " " + word
                        full_text += chunk
                        yield sse_event("token", {"text": chunk})

            history.append({"role": "assistant", "content": response.content})
            # Send updated history so frontend can pass it back next turn
            history_serializable = [
                {"role": m["role"], "content": m["content"] if isinstance(m["content"], str) else "[tool content]"}
                for m in history
            ]
            yield sse_event("done", {"history": history_serializable})
            break

        if response.stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    yield sse_event("tool_call", {"name": block.name, "input": block.input})
                    result = TOOL_FUNCTIONS.get(block.name, lambda **k: "Unknown tool")(**block.input)
                    yield sse_event("tool_result", {"result": result[:500]})  # truncate for UI
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            history.append({"role": "user", "content": tool_results})
            continue

        break

# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    """
    Accepts a POST with JSON body:
        {"message": "...", "history": [...], "model": "llama"|"claude"}
    ("model" is optional; the server default applies when omitted.)
    Streams back SSE events as the agent thinks and responds.

    Event types:
    - tool_call:   The model is calling a tool {name, input}
    - tool_result: The tool's output {result}
    - token:       A chunk of the model's text response {text}
    - done:        Signals the stream is complete {history}
    - error:       Something went wrong {message}
    """
    body = request.get_json() or {}
    user_message = body.get("message", "").strip()
    conversation_history = body.get("history", [])

    if not user_message:
        return {"error": "Empty message"}, 400

    backend = select_backend(body)

    # A deployed server has no local Ollama to start: when the picked
    # Llama backend cannot serve but Claude is configured, serve with
    # Claude instead of failing — a visitor cannot start Ollama on a
    # machine they don't own. On a personal install Ollama is running,
    # so this never triggers and Llama stays the default there.
    if backend == "llama" and not ollama_available(OLLAMA_HOST) \
            and get_claude_client() is not None:
        backend = "claude"

    # Fail fast and honestly, before streaming starts, when the chosen
    # backend cannot serve — the frontend turns a non-200 here into its
    # "PocketAI is not running on this computer" state.
    if backend == "llama" and not ollama_available(OLLAMA_HOST):
        return {
            "error": "PocketAI's local model (Ollama) is not running on "
                     "this computer. Start Ollama, then send your "
                     "message again."
        }, 503
    if backend == "claude" and get_claude_client() is None:
        return {
            "error": "Claude is not set up on this computer (no "
                     "Anthropic API key). Switch to Llama, or add your "
                     "key to config.py."
        }, 503

    def generate():
        if backend == "llama":
            yield from run_llama_chat(
                host=OLLAMA_HOST,
                model=OLLAMA_MODEL,
                system_prompt=SYSTEM_PROMPT,
                plain_history=conversation_history,
                user_message=user_message,
                tool_schemas=TOOL_SCHEMAS,
                tool_functions=TOOL_FUNCTIONS,
            )
        else:
            yield from generate_claude(conversation_history, user_message)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Prevents nginx from buffering the stream
        }
    )

@app.route("/agent-name", methods=["GET"])
def agent_name():
    """
    Returns the agent's name so the frontend can display it.
    Also reports which backends this server can serve, so the UI (and
    anyone debugging) can see the live model setup. The frontend only
    reads "name"; the extra fields change nothing for it.
    """
    return {
        "name": AGENT_NAME,
        "default_backend": DEFAULT_BACKEND,
        "backends": {
            "llama": {"model": OLLAMA_MODEL, "host": OLLAMA_HOST},
            "claude": {"model": MODEL, "configured": bool(ANTHROPIC_API_KEY)},
        },
    }

# ── Built frontend (deployed servers) ───────────────────────────────
# A deployed server also serves the Vite build in ../dist, so the
# site and its API share one origin. Locally that folder may not
# exist — the Vite dev server serves the UI there instead, and these
# routes just 404. The API routes above are more specific and always
# win over this catch-all.
DIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist"
)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.isfile(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    if os.path.isfile(os.path.join(DIST_DIR, "index.html")):
        return send_from_directory(DIST_DIR, "index.html")
    return {"error": "Frontend not built"}, 404


if __name__ == "__main__":
    print(f"Starting PocketAI server — agent name: {AGENT_NAME}")
    print(f"Default backend: {DEFAULT_BACKEND} "
          f"(llama: {OLLAMA_MODEL} at {OLLAMA_HOST}; claude: {MODEL or 'not configured'})")
    app.run(port=5001, debug=True)
