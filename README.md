# PocketAI

**Live:** https://pocketai-yiai.onrender.com

A local AI assistant that answers questions about your own files. Two frontends over one agentic loop: a terminal CLI and a React web UI, both backed by a Flask server that calls the Claude API. Claude can read files and PDFs, list directories, and search the web, then answer from what it found.

## Architecture

```
CLI (agent.py, Rich terminal UI) ──┐
                                    ▼
React + Vite chat UI ── POST /chat (SSE) ──▶ Flask (server/app.py, port 5001)
                                              │  agentic loop
                                              ▼
                                           Claude API (Anthropic)
                                              │  tool calls
                                              ▼
                              read_file · list_directory · read_pdf · search_web
                              (local files, PyMuPDF, DuckDuckGo)
```

- **CLI** (`agent.py`): interactive loop with a Rich terminal UI; 3 tools (read_file, list_directory, search_web).
- **Backend** (`server/app.py`): Flask, two routes — `POST /chat` runs the agentic loop and streams token, tool_call, tool_result, and done events over SSE; `GET /agent-name` returns the agent name. Adds read_pdf as a fourth tool. Runs on port 5001.
- **Frontend** (`src/App.jsx`): React + Vite chat UI — live token streaming, collapsible tool calls, message edit-and-resend, voice input (Web Speech API), clickable file paths. Talks to the backend at `http://localhost:5001`; dev server on port 5173.
- **Config**: `config.py` (gitignored, copied from `config.example.py`) holds the Anthropic API key, model (default claude-sonnet-4-20250514), and agent name; the agent name can also be saved in `~/.jemi/config.json`.

## Stack

Python · Flask · Anthropic Claude API · React 19 · Vite · PyMuPDF · DuckDuckGo

## Run it locally

```bash
pip install -r requirements.txt
cp config.example.py config.py   # add your Anthropic API key
python server/app.py             # backend on port 5001
# in another terminal:
npm install
npm run dev                      # frontend on http://localhost:5173
```

Or just the CLI: `python agent.py`. Without a key, both frontends explain what's missing instead of crashing.

## Notes

- Files are read locally, but their contents are sent to Anthropic's API so Claude can answer. The API key lives only in gitignored `config.py`.
