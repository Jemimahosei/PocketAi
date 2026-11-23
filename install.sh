#!/bin/bash
echo "Installing PocketAI (free, local Llama 3)..."
if ! command -v ollama &> /dev/null; then
  curl -fsSL https://ollama.ai/install.sh | sh
fi
ollama pull llama3.2
if [ -d ~/PocketAi ]; then cd ~/PocketAi && git pull
else git clone https://github.com/Jemimahosei/PocketAi.git ~/PocketAi && cd ~/PocketAi
fi
pip3 install -r requirements.txt
echo "USE_OLLAMA=true" > .env
echo "Starting PocketAI. Your browser chat opens at http://localhost:5001"
echo "Leave this window open while you use PocketAI; press Ctrl+C to stop it."
(sleep 3; open http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 2>/dev/null) &
python3 server/app.py
