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
python3 agent.py
