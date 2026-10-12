"""
server/app.py — Flask backend for PocketAI web UI

Exposes a single /chat endpoint that streams responses from the
agentic loop back to the React frontend using Server-Sent Events (SSE).
"""

import sys
import os
import json

# Add the project root to Python's path so we can import agent.py and config.py
# This is needed because server/app.py is in a subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS

from config import ANTHROPIC_API_KEY, MODEL, AGENT_NAME, MAX_TOKENS
from config_manager import get_agent_name
from tools.file_tool import read_file, list_directory
from tools.pdf_tool import read_pdf
from tools.search_tool import search_web
from anthropic import Anthropic

app = Flask(__name__)
CORS(app)  # Allow React dev server (port 5173) to talk to Flask (port 5000)

client = Anthropic(api_key=ANTHROPIC_API_KEY)
AGENT_NAME = get_agent_name(fallback=AGENT_NAME)

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

# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    """
    Accepts a POST with JSON body: {"message": "...", "history": [...]}
    Streams back SSE events as the agent thinks and responds.

    Event types:
    - tool_call:   Claude is calling a tool {name, input}
    - tool_result: The tool's output {result}
    - token:       A chunk of Claude's text response {text}
    - done:        Signals the stream is complete {history}
    - error:       Something went wrong {message}
    """
    body = request.get_json()
    user_message = body.get("message", "").strip()
    conversation_history = body.get("history", [])

    if not user_message:
        return {"error": "Empty message"}, 400

    def generate():
        history = conversation_history + [{"role": "user", "content": user_message}]

        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=(
                    f"You are {AGENT_NAME}, a helpful AI assistant running locally on the user's Mac. When asked about files, look in ~/Downloads, ~/Desktop, ~/Documents, and ~ by default. Use read_pdf for .pdf files, read_file for text files, list_directory to explore folders. "
                    "Be concise and direct. Use markdown formatting."
                ),
                tools=TOOL_SCHEMAS,
                messages=history,
            )

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
    """Returns the agent's name so the frontend can display it."""
    return {"name": AGENT_NAME}

if __name__ == "__main__":
    print(f"Starting PocketAI server — agent name: {AGENT_NAME}")
    app.run(port=5001, debug=True)
