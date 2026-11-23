"""
config_manager.py — Persistent user configuration

Stores user preferences (like agent name) in ~/.pocketai/config.json
so they persist across sessions without touching the code. Older
versions used ~/.jemi/config.json; that file is still read so an
existing name carries over.
"""

import json
import pathlib

# ~/.pocketai/ is the standard place for per-user app config on
# Mac/Linux. Using a dot-folder in home keeps it out of the way but
# easy to find.
CONFIG_DIR = pathlib.Path.home() / ".pocketai"
CONFIG_FILE = CONFIG_DIR / "config.json"
LEGACY_CONFIG_FILE = pathlib.Path.home() / ".jemi" / "config.json"


def load_config() -> dict:
    """
    Loads the saved config, preferring ~/.pocketai/config.json and
    falling back to the legacy ~/.jemi/config.json.
    Returns an empty dict if neither file exists or parses.
    """
    for path in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                # File exists but is corrupted — start fresh
                return {}
    return {}


def save_config(config: dict) -> None:
    """
    Saves config dict to ~/.pocketai/config.json.
    Creates the directory if it doesn't exist.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_agent_name(fallback: str = "PocketAI") -> str:
    """
    Returns the user's chosen agent name, or the fallback.

    Deliberately never prompts: this runs at startup, including in
    the middle of the one-command installs, where stopping to ask
    for a name is a confusing interruption (and writes a file the
    user never asked for). To use a different name, put
    {"agent_name": "..."} in ~/.pocketai/config.json.

    Args:
        fallback: Default name if none is saved.

    Returns:
        The agent name as a string.
    """
    return load_config().get("agent_name") or fallback
