# Jemi — AI Terminal Assistant

A CLI AI agent built with the Claude API that can read files, browse directories, and search the web — all from your terminal.

## Features

- **Agentic loop** — Claude decides when to call tools and chains multiple calls when needed
- **File tools** — read any file, list any directory
- **Web search** — DuckDuckGo instant answers, no API key required
- **Rich terminal UI** — spinner, color-coded panels for tool calls and responses
- **Conversation memory** — full message history kept across turns in a session

## Stack

- Python 3.11
- Anthropic Claude API (claude-haiku-4-5-20251001)
- Rich — terminal UI
- DuckDuckGo Instant Answer API — free, no key needed

## Setup

    git clone https://github.com/Jemimahosei/jemi-agent.git
    cd jemi-agent
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create config.py (gitignored):

    ANTHROPIC_API_KEY = "your-key-here"
    MODEL = "claude-haiku-4-5-20251001"
    AGENT_NAME = "Jemi"
    MAX_TOKENS = 4096

Run:

    python agent.py

## Project Structure

    jemi-agent/
    ├── agent.py           # Agentic loop, UI, entry point
    ├── config.py          # API key and model config (gitignored)
    ├── tools/
    │   ├── file_tool.py   # read_file, list_directory
    │   └── search_tool.py # search_web via DuckDuckGo
    ├── requirements.txt
    └── ARCHITECTURE.md

## Roadmap

- Ollama support for offline/local model inference
- Web UI (Flask + React) with streaming responses
- MCP server integration for extended tool ecosystem
- Shell execution tool
