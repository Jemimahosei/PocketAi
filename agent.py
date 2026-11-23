"""
agent.py — Jemi CLI AI Agent

Agentic loop: sends user messages to the chosen model backend —
Claude (Anthropic API) or Llama 3.2 on a local Ollama server —
handles tool calls, and displays results with a rich terminal UI.
Switch backends at startup (--claude / --llama) or mid-chat with
the /claude and /llama commands.
"""

import os
import sys

try:
    import readline  # noqa: F401 — arrow keys / line editing at the prompt
except ImportError:
    pass

from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.rule import Rule
from rich import box

# config.py is optional: it carries the Claude settings. Without it
# the terminal still runs on the free local Llama backend.
try:
    import config as _config
except ModuleNotFoundError:
    _config = None


def _cfg(name, default=None):
    return getattr(_config, name, default) if _config is not None else default


ANTHROPIC_API_KEY = _cfg("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
MODEL = _cfg("MODEL", "claude-sonnet-5")
AGENT_NAME = _cfg("AGENT_NAME", "PocketAI")
MAX_TOKENS = int(_cfg("MAX_TOKENS", 1024))
OLLAMA_HOST = _cfg("OLLAMA_HOST") or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = _cfg("OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL", "llama3.2")

CLAUDE_AVAILABLE = bool(ANTHROPIC_API_KEY) and "your-api-key" not in str(ANTHROPIC_API_KEY)

from config_manager import get_agent_name
from tools.file_tool import read_file, list_directory
from tools.pdf_tool import read_pdf
from tools.search_tool import search_web

# The Llama backend lives with the web server's code; reuse it so the
# terminal and the website talk to Ollama in exactly the same way.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))
try:
    import ollama_backend
except ImportError:  # the module ships with the repo; belt and braces
    ollama_backend = None

# ── Client & UI setup ────────────────────────────────────────────────────────

client = None
if CLAUDE_AVAILABLE:
    # Never advertise brotli ("br"): some machines ship a brotli build whose
    # Decompressor lacks the output_buffer_limit argument httpx2 passes, which
    # crashed every Claude reply with a TypeError surfaced as "Connection error".
    client = Anthropic(
        api_key=ANTHROPIC_API_KEY,
        default_headers={"Accept-Encoding": "gzip, deflate"},
    )
console = Console()

# Load agent name from ~/.pocketai/config.json if one exists (never prompts)
AGENT_NAME = get_agent_name(fallback=AGENT_NAME)

SYSTEM_PROMPT = (
    f"You are {AGENT_NAME}, a helpful AI assistant running in the terminal. "
    "Be concise and direct. Use markdown formatting in your responses. "
    "Use read_pdf for PDF files and read_file for plain text files. "
    "When asked about files, look in ~/Downloads, ~/Desktop, ~/Documents, and ~ by default; "
    "if a folder does not exist or a file is not in the first place you look, keep trying the other default folders before giving up. "
    "For questions about the user's own files, use the file tools — never search_web; search_web is only for facts about the outside world. "
    "When a file you found likely answers the question, read it and answer from its contents. "
    "Do not ask the user for permission to look at a folder — just look."
)

# ── Tool schemas (what we tell Claude it can call) ────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the local filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read."
                }
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
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Defaults to current directory.",
                    "default": "."
                }
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
                "path": {
                    "type": "string",
                    "description": "Path to the PDF file to read."
                }
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
                "query": {
                    "type": "string",
                    "description": "The search query."
                }
            },
            "required": ["query"]
        }
    }
]

# Maps tool name → actual Python function
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "read_pdf": read_pdf,
    "search_web": search_web,
}

# ── Tool execution ────────────────────────────────────────────────────────────

def run_tool(tool_name: str, tool_input: dict) -> str:
    """
    Dispatches a tool call from Claude to the correct Python function.

    Args:
        tool_name:  Name of the tool Claude wants to call.
        tool_input: Arguments Claude is passing to the tool.

    Returns:
        The tool's output as a string.
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: unknown tool '{tool_name}'"
    return TOOL_FUNCTIONS[tool_name](**tool_input)

# ── UI helpers ────────────────────────────────────────────────────────────────

def print_tool_call(tool_name: str, tool_input: dict) -> None:
    """Renders a tool call as a compact panel."""
    args = ", ".join(f"{k}={repr(v)}" for k, v in tool_input.items())
    console.print(
        Panel(
            f"[bold cyan]{tool_name}[/bold cyan]([yellow]{args}[/yellow])",
            title="[dim]tool call[/dim]",
            border_style="dim cyan",
            padding=(0, 1),
        )
    )

def print_tool_result(result: str) -> None:
    """Renders a tool result as a dim panel."""
    # Truncate very long results for display
    display = result if len(result) <= 600 else result[:600] + "\n[dim]… (truncated)[/dim]"
    console.print(
        Panel(
            display,
            title="[dim]result[/dim]",
            border_style="dim green",
            padding=(0, 1),
        )
    )

def print_jemi_response(text: str) -> None:
    """Renders Jemi's final response as a markdown panel."""
    console.print(
        Panel(
            Markdown(text),
            title=f"[bold magenta]{AGENT_NAME}[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

# ── Agentic loops ─────────────────────────────────────────────────────────────

def _friendly_claude_error(e: Exception) -> str:
    """Short, user-readable version of an Anthropic API failure —
    never a traceback or the raw error dump."""
    status = getattr(e, "status_code", None)
    kind = type(e).__name__
    if status == 401 or kind == "AuthenticationError":
        return ("Your Anthropic API key was rejected. Check "
                "ANTHROPIC_API_KEY in config.py and ask again.")
    if kind == "APIConnectionError":
        return ("I couldn't reach Claude just now — check the internet "
                "connection and ask again.")
    if status == 404:
        return (f"The model {MODEL} was not found for your API key. "
                "Check MODEL in config.py.")
    if status == 429:
        return ("Claude is rate-limiting this key right now. Wait a "
                "moment and ask again.")
    return "Claude could not answer just now. Try again in a moment."


def chat_claude(user_message: str, conversation_history: list) -> tuple[str, list]:
    """
    Sends a user message through the Claude agentic loop.

    Handles multi-step tool use: Claude may call tools, receive results,
    then call more tools before giving a final answer.

    Args:
        user_message:          The user's input string.
        conversation_history:  Running list of messages (mutated in place).

    Returns:
        (final_text, updated_history)
    """
    conversation_history.append({"role": "user", "content": user_message})

    while True:
        try:
            with Live(Spinner("dots", text=" thinking…", style="dim"), console=console, refresh_per_second=10):
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_SCHEMAS,
                    messages=conversation_history,
                )
        except Exception as e:
            conversation_history.pop()  # take back the unanswered message
            return _friendly_claude_error(e), conversation_history

        # ── End turn: Claude has a final answer ──────────────────────────────
        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            conversation_history.append({"role": "assistant", "content": response.content})
            return final_text, conversation_history

        # ── Tool use: Claude wants to call one or more tools ─────────────────
        if response.stop_reason == "tool_use":
            conversation_history.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print_tool_call(block.name, block.input)
                    result = run_tool(block.name, block.input)
                    print_tool_result(result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            conversation_history.append({"role": "user", "content": tool_results})
            # Loop — Claude will now respond to the tool results
            continue

        # Unexpected stop reason
        break

    return "Something went wrong — unexpected stop reason.", conversation_history


def chat_llama(user_message: str, conversation_history: list) -> tuple[str, list]:
    """
    The same agentic loop as chat_claude, served by Llama 3.2 on a
    local Ollama server (via server/ollama_backend.py, shared with
    the web chat). The stored history stays plain {"role", "content"}
    text entries; tool rounds live in the per-turn message list.
    """
    if ollama_backend is None:
        return ("The Llama backend is missing (server/ollama_backend.py).",
                conversation_history)

    tools = ollama_backend.to_ollama_tools(TOOL_SCHEMAS)
    messages = ollama_backend.to_ollama_messages(SYSTEM_PROMPT, conversation_history)
    messages.append({"role": "user", "content": user_message})

    nudges = 0
    try:
        for _round in range(ollama_backend.MAX_TOOL_ROUNDS):
            full_text = ""
            pending_calls = []
            with Live(Spinner("dots", text=" thinking…", style="dim"), console=console, refresh_per_second=10):
                for content, tool_calls in ollama_backend.stream_ollama_chat(
                    OLLAMA_HOST, OLLAMA_MODEL, messages, tools
                ):
                    full_text += content
                    pending_calls.extend(tool_calls)

            if not pending_calls:
                # Same recovery as the web chat: a call written as text
                # gets a correction round instead of ending the turn.
                text_call = (ollama_backend.find_text_tool_call(full_text, TOOL_FUNCTIONS)
                             if nudges < 3 else None)
                if text_call is not None:
                    nudges += 1
                    messages.append({"role": "assistant", "content": full_text})
                    messages.append({"role": "user", "content":
                                     ollama_backend.text_call_nudge(text_call[0], text_call[1])})
                    continue
                conversation_history.append({"role": "user", "content": user_message})
                conversation_history.append({"role": "assistant", "content": full_text})
                return full_text, conversation_history

            messages.append({
                "role": "assistant",
                "content": full_text,
                "tool_calls": [c["raw"] for c in pending_calls],
            })
            for call in pending_calls:
                print_tool_call(call["name"], call["arguments"])
                result = run_tool(call["name"], call["arguments"])
                print_tool_result(result)
                messages.append({
                    "role": "tool",
                    "tool_name": call["name"],
                    "content": result,
                })
            # Loop — Llama now answers (or asks for more tools).

        return ("The local model kept asking for tools and never settled "
                "on an answer. Try asking again, a little more simply.",
                conversation_history)
    except ollama_backend.OllamaUnavailable:
        return ("The local model (Ollama) is not running. Start Ollama "
                "and ask again — or type /claude to switch to Claude.",
                conversation_history)
    except ollama_backend.OllamaError as e:
        return (f"Ollama said: {e}. If the model is missing, run: "
                f"ollama pull {OLLAMA_MODEL}", conversation_history)

# ── Entry point ───────────────────────────────────────────────────────────────

def _backend_label(backend: str) -> str:
    return f"Claude ({MODEL})" if backend == "claude" else f"Llama ({OLLAMA_MODEL}, on this computer)"


def main() -> None:
    """Interactive CLI loop with rich terminal UI."""
    args = sys.argv[1:]
    llama_ok = ollama_backend is not None and ollama_backend.ollama_available(OLLAMA_HOST)

    if "--llama" in args:
        backend = "llama"
    elif "--claude" in args:
        backend = "claude"
    elif CLAUDE_AVAILABLE:
        backend = "claude"
    else:
        backend = "llama"

    # If the chosen backend cannot serve, start on the other one when
    # it can — and say so. If neither can, explain the two setups.
    available = {"claude": CLAUDE_AVAILABLE, "llama": llama_ok}
    if not available[backend]:
        other = "llama" if backend == "claude" else "claude"
        if available[other]:
            console.print(
                f"[dim]{_backend_label(backend)} isn't available, so this "
                f"session starts on {_backend_label(other)} instead.[/dim]"
            )
            backend = other
        else:
            console.print(
                "PocketAI needs one of its two models before it can chat:\n"
                "  • Claude — copy the settings template and paste in an "
                "Anthropic API key:\n"
                "        cp config.example.py config.py\n"
                "  • Llama (free, local) — install and start Ollama:\n"
                "        https://ollama.com  — then: ollama pull llama3.2"
            )
            sys.exit(1)

    console.print()
    console.print(Panel(
        f"[bold magenta]{AGENT_NAME}[/bold magenta] — [dim]AI Terminal Assistant[/dim]\n"
        f"[dim]Backend: [bold]{_backend_label(backend)}[/bold] · switch with [bold]/claude[/bold] or [bold]/llama[/bold][/dim]\n"
        "[dim]Type [bold]quit[/bold] or [bold]exit[/bold] to stop[/dim]\n"
        "[dim]Try: [italic]list my files[/italic] · [italic]read agent.py[/italic] · [italic]search for …[/italic][/dim]",
        border_style="magenta",
        box=box.DOUBLE,
        padding=(1, 3),
    ))
    console.print()

    # Each backend keeps its own thread, so switching back resumes it.
    histories: dict = {"claude": [], "llama": []}

    while True:
        try:
            user_input = console.input("[bold green]You ▶[/bold green]  ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)

        if not user_input:
            continue
        lowered = user_input.lower()
        if lowered in {"quit", "exit"}:
            console.print(Panel("[dim]Goodbye! 👋[/dim]", border_style="dim"))
            break

        if lowered in {"/claude", "/llama", "/model"}:
            if lowered == "/model":
                console.print(
                    f"[dim]Now: {_backend_label(backend)} · "
                    f"Claude: {'ready' if CLAUDE_AVAILABLE else 'no API key'} · "
                    f"Llama: {'ready' if llama_ok else 'Ollama not running'}[/dim]"
                )
                continue
            target = lowered[1:]
            if target == backend:
                console.print(f"[dim]Already on {_backend_label(backend)}.[/dim]")
            elif not available[target]:
                reason = ("no Anthropic API key in config.py" if target == "claude"
                          else "Ollama is not running on this computer")
                console.print(f"[dim]Can't switch to {_backend_label(target)} — {reason}.[/dim]")
            else:
                backend = target
                console.print(f"[dim]Switched to {_backend_label(backend)}.[/dim]")
            continue

        console.print()
        try:
            if backend == "claude":
                response_text, histories["claude"] = chat_claude(user_input, histories["claude"])
            else:
                response_text, histories["llama"] = chat_llama(user_input, histories["llama"])
        except Exception as e:  # never show the user a traceback
            response_text = f"Something went wrong: {e}"
        console.print()
        print_jemi_response(response_text)
        console.print()

if __name__ == "__main__":
    main()
