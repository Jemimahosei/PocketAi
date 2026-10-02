"""
agent.py — Jemi CLI AI Agent

Agentic loop: sends user messages to Claude, handles tool calls,
and displays results with a rich terminal UI.
"""

import sys
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.rule import Rule
from rich import box

from config import ANTHROPIC_API_KEY, MODEL, AGENT_NAME, MAX_TOKENS
from config_manager import get_agent_name
from tools.file_tool import read_file, list_directory
from tools.search_tool import search_web

# ── Client & UI setup ────────────────────────────────────────────────────────

client = Anthropic(api_key=ANTHROPIC_API_KEY)
console = Console()

# Load agent name from ~/.jemi/config.json (runs first-run setup if needed)
AGENT_NAME = get_agent_name(fallback=AGENT_NAME)

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

# ── Agentic loop ──────────────────────────────────────────────────────────────

def chat(user_message: str, conversation_history: list) -> tuple[str, list]:
    """
    Sends a user message through the agentic loop.

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
        with Live(Spinner("dots", text=" thinking…", style="dim"), console=console, refresh_per_second=10):
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=(
                    f"You are {AGENT_NAME}, a helpful AI assistant running in the terminal. "
                    "Be concise and direct. Use markdown formatting in your responses."
                ),
                tools=TOOL_SCHEMAS,
                messages=conversation_history,
            )

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

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Interactive CLI loop with rich terminal UI."""
    console.print()
    console.print(Panel(
        f"[bold magenta]{AGENT_NAME}[/bold magenta] — [dim]AI Terminal Assistant[/dim]\n"
        "[dim]Type [bold]quit[/bold] or [bold]exit[/bold] to stop[/dim]\n"
        "[dim]Try: [italic]list my files[/italic] · [italic]read agent.py[/italic] · [italic]search for …[/italic][/dim]",
        border_style="magenta",
        box=box.DOUBLE,
        padding=(1, 3),
    ))
    console.print()

    conversation_history: list = []

    while True:
        try:
            user_input = console.input("[bold green]You ▶[/bold green]  ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            console.print(Panel("[dim]Goodbye! 👋[/dim]", border_style="dim"))
            break

        console.print()
        response_text, conversation_history = chat(user_input, conversation_history)
        console.print()
        print_jemi_response(response_text)
        console.print()

if __name__ == "__main__":
    main()
