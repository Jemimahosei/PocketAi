"""
server/ollama_backend.py — Llama backend for the PocketAI web server

Talks to a local Ollama server (https://ollama.com) over its HTTP chat
API using only the Python standard library (urllib), so the Llama path
needs no API key and no new pip packages.

Ollama's /api/chat endpoint supports tool calling for Llama 3.2: it
accepts tools in an OpenAI-style {"type": "function", ...} shape and
answers with message.tool_calls entries whose function.arguments is a
JSON object. This module translates PocketAI's Anthropic-style tool
schemas to that shape and runs the same tool-use loop the Claude path
runs, emitting the exact SSE events the React frontend already
understands: token / tool_call / tool_result / done / error.
"""

import json
import urllib.error
import urllib.request

# How long to wait for Ollama to answer a liveness check (seconds).
TAGS_TIMEOUT = 2
# How long a single /api/chat read may block (seconds). Local models
# can be slow to produce the first chunk on a cold start.
CHAT_TIMEOUT = 180
# Safety net so a model that keeps asking for tools forever cannot
# loop the server indefinitely.
MAX_TOOL_ROUNDS = 10


class OllamaUnavailable(Exception):
    """Ollama is not reachable at all (not installed / not running)."""


class OllamaError(Exception):
    """Ollama answered, but with an error (e.g. model not pulled)."""


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _request(host: str, path: str, payload, timeout: float):
    """Opens a request to the Ollama server, translating failures."""
    url = host.rstrip("/") + path
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        # Ollama sends {"error": "..."} bodies, e.g. when the model has
        # not been pulled yet. Surface that text, never a stack trace.
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", "")
        except Exception:
            pass
        raise OllamaError(detail or f"Ollama returned HTTP {e.code}") from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise OllamaUnavailable(str(e)) from e


def ollama_available(host: str) -> bool:
    """True if an Ollama server answers at host (GET /api/tags)."""
    try:
        with _request(host, "/api/tags", None, TAGS_TIMEOUT) as resp:
            return resp.status == 200
    except (OllamaUnavailable, OllamaError):
        return False


# ── Schema / message translation ─────────────────────────────────────────────

def to_ollama_tools(tool_schemas: list) -> list:
    """
    Translates Anthropic-style tool schemas
    ({name, description, input_schema}) into Ollama's OpenAI-style
    tool format ({type: "function", function: {name, description,
    parameters}}). The parameter JSON Schema is carried over as-is.
    """
    tools = []
    for schema in tool_schemas:
        tools.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return tools


def to_ollama_messages(system_prompt: str, plain_history: list) -> list:
    """
    Converts the frontend's plain history ([{"role", "content": str}])
    into Ollama chat messages, prefixed with the system prompt.
    Entries with non-string content (e.g. serialised tool blocks from
    the Claude path) are skipped — they carry no readable text.
    """
    messages = [{"role": "system", "content": system_prompt}]
    for entry in plain_history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})
    return messages


def _parse_arguments(raw) -> dict:
    """Ollama returns function.arguments as an object; older/newer
    builds may send a JSON string. Accept both, never crash."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


# ── Streaming chat ───────────────────────────────────────────────────────────

def stream_ollama_chat(host: str, model: str, messages: list, tools: list):
    """
    Streams one /api/chat round. Yields (content_delta, tool_calls)
    tuples as chunks arrive; the final yield has done=True semantics
    conveyed by the caller exhausting the generator. tool_calls is a
    list of {"name": str, "arguments": dict} (possibly empty).
    """
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": True,
        # Ollama's default temperature (0.8) is tuned for creative chat;
        # an agent deciding tool calls does better cooler — at 0.8 the
        # 3B model sometimes narrates the next tool result instead of
        # calling the tool. 0.3 keeps wording natural but steadier.
        "options": {"temperature": 0.3},
    }
    with _request(host, "/api/chat", payload, CHAT_TIMEOUT) as resp:
        for line in resp:
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            message = chunk.get("message") or {}
            content = message.get("content") or ""
            tool_calls = []
            for call in message.get("tool_calls") or []:
                fn = call.get("function") or {}
                if fn.get("name"):
                    tool_calls.append({
                        "name": fn["name"],
                        "arguments": _parse_arguments(fn.get("arguments")),
                        # Keep the raw call so it can be echoed back to
                        # Ollama in the follow-up round verbatim.
                        "raw": call,
                    })
            if content or tool_calls:
                yield content, tool_calls
            if chunk.get("done"):
                break


# ── The agentic loop (SSE) ───────────────────────────────────────────────────

def find_text_tool_call(text, known_tools):
    """Detects a tool call the model wrote as plain-text JSON instead of
    using the tool-calling format — something small local models do after
    a few rounds, which would otherwise end the turn with the raw JSON
    shown to the user as if it were the answer. Returns (name, args) for
    the first JSON object in the text that names a known tool, else None.
    """
    if not text:
        return None
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[i:])
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("name") in known_tools:
            args = (obj.get("parameters") or obj.get("arguments")
                    or obj.get("input") or {})
            return obj["name"], args if isinstance(args, dict) else {}
    return None


# Each file/search tool's main argument — used to repair a text-written
# call whose argument has the wrong name (models invent e.g. "fp").
PRIMARY_ARG = {
    "read_file": "path",
    "read_pdf": "path",
    "list_directory": "path",
    "search_web": "query",
}


def text_call_nudge(name: str, args: dict = None) -> str:
    """The correction fed back when find_text_tool_call fires. When the
    written-out call carried a usable argument, the correction spells
    out the exact call to make — small models follow a concrete example
    far better than a format lecture."""
    message = (
        f"You wrote that {name} call as plain text, which does not run "
        "it. Call the tool now, using the tool-calling format — do not "
        "write the call out as JSON text."
    )
    primary = PRIMARY_ARG.get(name)
    if args and primary:
        if primary not in args:
            strings = [v for v in args.values() if isinstance(v, str)]
            if len(strings) == 1:
                args = {primary: strings[0]}
        if primary in args:
            message += (f" Make exactly this call: {name} with "
                        f"{primary} = {args[primary]!r}.")
    return message


def _sse(event: str, data: dict) -> str:
    """Formats a Server-Sent Event string (same shape as app.py)."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def run_llama_chat(host: str, model: str, system_prompt: str,
                   plain_history: list, user_message: str,
                   tool_schemas: list, tool_functions: dict):
    """
    Generator that runs the Llama tool-use loop and yields SSE event
    strings with the same shapes the Claude path in app.py emits:

    - tool_call:   {"name", "input"}
    - tool_result: {"result"} (truncated to 500 chars for the UI)
    - token:       {"text"}
    - done:        {"history"} — plain {"role", "content"} entries
    - error:       {"message"} — clean, user-readable, no stack traces
    """
    tools = to_ollama_tools(tool_schemas)
    messages = to_ollama_messages(system_prompt, plain_history)
    messages.append({"role": "user", "content": user_message})
    done_history = list(plain_history) + [{"role": "user", "content": user_message}]

    nudges = 0
    try:
        for _round in range(MAX_TOOL_ROUNDS):
            full_text = ""
            pending_calls = []
            for content, tool_calls in stream_ollama_chat(host, model, messages, tools):
                if content:
                    full_text += content
                    yield _sse("token", {"text": content})
                pending_calls.extend(tool_calls)

            if not pending_calls:
                # A call written as text instead of in tool format gets
                # a correction round rather than ending the turn with
                # raw JSON as the "answer". Models often need the
                # correction more than once in a single turn (each miss
                # is a different file), so allow a few — MAX_TOOL_ROUNDS
                # still bounds the turn.
                text_call = (find_text_tool_call(full_text, tool_functions)
                             if nudges < 3 else None)
                if text_call is not None:
                    nudges += 1
                    messages.append({"role": "assistant", "content": full_text})
                    messages.append({"role": "user", "content":
                                     text_call_nudge(text_call[0], text_call[1])})
                    continue
                # Final answer — mirror the Claude path's done event.
                done_history.append({"role": "assistant", "content": full_text})
                yield _sse("done", {"history": done_history})
                return

            # Echo the assistant's tool calls back, then run each tool
            # and feed results in as role:"tool" messages.
            messages.append({
                "role": "assistant",
                "content": full_text,
                "tool_calls": [c["raw"] for c in pending_calls],
            })
            for call in pending_calls:
                name = call["name"]
                args = call["arguments"]
                yield _sse("tool_call", {"name": name, "input": args})
                fn = tool_functions.get(name)
                if fn is None:
                    result = f"Error: unknown tool '{name}'"
                else:
                    try:
                        result = fn(**args)
                    except TypeError as e:
                        result = f"Error calling {name}: {e}"
                    except Exception as e:  # tools return strings, but never hang the stream
                        result = f"Error calling {name}: {e}"
                if not isinstance(result, str):
                    result = str(result)
                yield _sse("tool_result", {"result": result[:500]})
                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": result,
                })
            # Loop — Llama now answers (or asks for more tools).

        yield _sse("error", {
            "message": "PocketAI's local model kept asking for tools and "
                       "never settled on an answer. Try asking again, "
                       "a little more simply."
        })
    except OllamaUnavailable:
        yield _sse("error", {
            "message": "PocketAI's local model (Ollama) is not running "
                       "on this computer. Start Ollama, then send your "
                       "message again."
        })
    except OllamaError as e:
        yield _sse("error", {
            "message": f"Ollama said: {e}. If the model is missing, "
                       f"run: ollama pull {model}"
        })
