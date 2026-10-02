"""
config_manager.py — Persistent user configuration

Stores user preferences (like agent name) in ~/.jemi/config.json
so they persist across sessions without touching the code.
"""

import json
import pathlib
from rich.console import Console
from rich.panel import Panel

# ~/.jemi/ is the standard place for per-user app config on Mac/Linux
# Using a dot-folder in home keeps it out of the way but easy to find
CONFIG_DIR = pathlib.Path.home() / ".jemi"
CONFIG_FILE = CONFIG_DIR / "config.json"

console = Console()


def load_config() -> dict:
    """
    Loads the saved config from ~/.jemi/config.json.
    Returns an empty dict if the file doesn't exist yet.
    """
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            # File exists but is corrupted — start fresh
            return {}
    return {}


def save_config(config: dict) -> None:
    """
    Saves config dict to ~/.jemi/config.json.
    Creates the directory if it doesn't exist.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_agent_name(fallback: str = "Jemi") -> str:
    """
    Returns the user's chosen agent name.
    If none is saved, runs first-run setup to ask for one.

    Args:
        fallback: Default name if setup is skipped or fails.

    Returns:
        The agent name as a string.
    """
    config = load_config()

    if "agent_name" in config:
        return config["agent_name"]

    # First run — ask the user what to call their agent
    return _first_run_setup(config, fallback)


def _first_run_setup(config: dict, fallback: str) -> str:
    """
    Runs on first launch only. Asks the user to name their agent
    and saves the choice for all future sessions.

    Args:
        config:   Current config dict (may be empty).
        fallback: Name to use if the user skips the prompt.

    Returns:
        The chosen agent name.
    """
    console.print()
    console.print(Panel(
        "[bold magenta]Welcome! Looks like this is your first time.[/bold magenta]\n\n"
        "Let's personalize your agent.\n"
        "[dim]You can change this anytime by editing [bold]~/.jemi/config.json[/bold][/dim]",
        border_style="magenta",
        padding=(1, 2),
    ))
    console.print()

    try:
        name = console.input(
            f"[bold green]What do you want to call your agent?[/bold green] "
            f"[dim](press Enter to use '{fallback}')[/dim]  "
        ).strip()
    except (KeyboardInterrupt, EOFError):
        name = ""

    # Use fallback if they just pressed Enter or Ctrl+C
    if not name:
        name = fallback

    config["agent_name"] = name
    save_config(config)

    console.print()
    console.print(f"[dim]Got it! Your agent is named [bold magenta]{name}[/bold magenta]. "
                  f"Saved to ~/.jemi/config.json[/dim]")
    console.print()

    return name
