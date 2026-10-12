# PocketAI — An AI That Knows Your Computer

> **[▶ Try the live demo → pocket-ai-sage.vercel.app](https://pocket-ai-sage.vercel.app)**

Most AI assistants live in the cloud and know nothing about you. PocketAI runs locally on your Mac and can actually see your files, read your PDFs, search your folders, and answer questions about *your* stuff — not just the internet.

Ask it things like:
- "Summarize the PDF in my Downloads folder"
- "What files did I add to Desktop this week?"
- "Read my notes.txt and help me turn it into an email"
- "Search the web for internships and save the results to a file"

---

## Run it in one command

Free — no API key, powered by Llama 3:

    curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install.sh | bash

Smarter responses — powered by Claude (~$5/month):

    curl -fsSL https://raw.githubusercontent.com/Jemimahosei/PocketAi/main/install-claude.sh | bash

---

## What it can do

- Read any file on your computer (.txt, .pdf, .py, .md, .csv and more)
- Browse your folders and find files by name
- Search the web without needing an API key
- Voice input — speak your message instead of typing
- Edit messages — click to edit and resend any message
- Streams responses live as it thinks
- Runs entirely on your machine — your files never leave your computer

---

## Stack

- Python + Flask (backend with SSE streaming)
- React + Vite (frontend)
- Claude API or Ollama (your choice of AI model)
- pymupdf for PDF reading
- DuckDuckGo for free web search

---

## Manual Setup

    git clone https://github.com/Jemimahosei/PocketAi.git
    cd PocketAi
    pip install -r requirements.txt

Add your API key to config.py (already in .gitignore):

    ANTHROPIC_API_KEY = "your-key-here"

Start it:

    python server/app.py

Open http://localhost:5173 in your browser.
