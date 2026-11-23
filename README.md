# PocketAI

**Live:** https://pocketai-yiai.onrender.com

A personal AI assistant that answers questions about your own files. It runs in two places — a browser chat and a terminal chat — and either one can be powered by two models:

- **Llama 3.2** via [Ollama](https://ollama.com): free, runs entirely on your computer, no account or API key. Nothing leaves your machine.
- **Claude** via the Anthropic API: sharper on long documents. The text of files you ask about is sent to Anthropic; nothing else is.

Whichever model you pick, PocketAI can read files and PDFs, list folders, and search the web, then answer from what it found. In the browser chat the model switch is in the sidebar; in the terminal, use `/claude` and `/llama` (or start with `--claude` / `--llama`). Each chat only ever uses the model you picked — there is no silent fallback from one to the other.

## Install (one command)

**Free, with Llama:**

```bash
curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install.sh -o /tmp/pocketai-install.sh && bash /tmp/pocketai-install.sh
```

Installs Ollama if needed, downloads Llama 3.2, installs the Python packages, then starts PocketAI and opens the browser chat at http://localhost:5001.

**Smarter, with Claude:**

```bash
curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install-claude.sh -o /tmp/pocketai-install-claude.sh && bash /tmp/pocketai-install-claude.sh
```

Asks for an Anthropic API key once, saves it in `config.py` on your computer, then starts PocketAI the same way. Prefer the terminal? Either install also gives you `python3 agent.py`.

## Run it manually

```bash
pip install -r requirements.txt
ollama pull llama3.2             # for the free local model
cp config.example.py config.py   # optional — only for Claude; add your API key
python3 server/app.py            # browser chat at http://localhost:5001
python3 agent.py                 # or the terminal chat
```

`config.py` is gitignored. Settings can also come from environment variables (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `POCKETAI_BACKEND`, `OLLAMA_HOST`, `OLLAMA_MODEL`). The default Claude model is `claude-sonnet-5`. The agent name can also be saved in `~/.pocketai/config.json`.

## Uninstall

Delete the folder and the settings folder — that's everything:

```bash
rm -rf ~/PocketAi ~/.pocketai
```

If you installed the free version, Ollama and the downloaded Llama model stay behind (other apps may use them); `ollama rm llama3.2` removes the model.

## The hosted demo

The live site runs the same server, with two differences that matter:

- **File tools are off.** A hosted server must never read files for visitors — not theirs (it can't reach them) and not its own (its environment holds the API key). The hosted chat still answers questions and searches the web, and it says plainly that file access needs the local install. (`POCKETAI_FILE_TOOLS=off`, and automatic whenever Render's `RENDER` variable is present.)
- **The default model is Claude** (`POCKETAI_BACKEND=claude`), because no Ollama runs on a server. Picking Llama there gets an honest "not available" instead of a quiet swap.

## Architecture

```
Terminal (agent.py, Rich UI) ──┐
                               ├── agentic loop ── Claude API (Anthropic)
Browser chat (React + Vite) ───┘        │
   POST /chat (SSE) ──▶ Flask (server/app.py, port 5001)
                                        └── or Llama 3.2 via Ollama (server/ollama_backend.py)
                               tools: read_file · list_directory · read_pdf · search_web
```

- **Backend** (`server/app.py`): `POST /chat` runs the agentic loop for the chosen backend and streams token, tool_call, tool_result, and done events over SSE; `GET /agent-name` reports the agent name, which backends can actually serve right now, and whether the file tools are on. On a deployed server it also serves the built frontend from `dist/`.
- **Frontend** (`src/`): React + Vite — live token streaming, collapsible tool calls, message edit-and-resend, voice input (Web Speech API), a "files it opened" sidebar, and the model switch. In development it talks to the backend at `http://localhost:5001` (Vite dev server on port 5173).
- **Tools** (`tools/`): file and PDF reading (pypdf — deliberately light; the previous PDF library dragged in a ~180 MB machine-learning runtime for basic text extraction), directory listing, and DuckDuckGo web search, shared by both interfaces and both models.

## Stack

Python · Flask · Anthropic Claude API · Ollama (Llama 3.2) · React 19 · Vite · pypdf · DuckDuckGo
