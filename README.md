# PocketAI — Your Personal AI Agent

A local AI agent with a web UI and terminal interface. Chat with an AI that can read your files, browse directories, search the web, and read PDFs — running on your machine.

## Run it in one command

Free (Llama 3, no API key):

    curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install.sh | bash

Smarter (Claude API):

    curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install-claude.sh | bash

## Features

- Web UI — React frontend with streaming responses
- Voice input — speak your message with the mic button
- File tools — read any file, list any directory
- PDF reading — extract text from PDF files
- Web search — no API key required
- Edit messages — click pencil icon to edit and resend
- File path links — click any file path to copy it

## Stack

- Python 3.11 + Flask (backend, SSE streaming)
- React + Vite (frontend)
- Anthropic Claude API or Ollama (local, free)
- pymupdf — PDF reading
- DuckDuckGo — free web search

## Manual Setup

    git clone https://github.com/Jemimahosei/PocketAi.git
    cd PocketAi
    pip install -r requirements.txt

Create config.py (not committed):

    ANTHROPIC_API_KEY = "your-key-here"
    MODEL = "claude-haiku-4-5-20251001"
    AGENT_NAME = "PocketAI"
    MAX_TOKENS = 4096

Start backend:

    python server/app.py

Start frontend (new terminal):

    cd pocketai-client
    npm install && npm run dev

Open http://localhost:5173

## Project Structure

    PocketAi/
    ├── server/app.py
    ├── tools/
    │   ├── file_tool.py
    │   ├── search_tool.py
    │   └── pdf_tool.py
    ├── config_manager.py
    ├── requirements.txt
    ├── install.sh
    ├── install-claude.sh
    └── pocketai-client/

## Roadmap

- Ollama support for free local inference
- Shell execution tool
- Deploy web version with domain
