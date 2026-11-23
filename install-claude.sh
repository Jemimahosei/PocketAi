#!/bin/bash
echo "Installing PocketAI (Claude)..."
if [ -d ~/PocketAi ]; then cd ~/PocketAi && git pull
else git clone https://github.com/Jemimahosei/PocketAi.git ~/PocketAi && cd ~/PocketAi
fi
pip3 install -r requirements.txt
echo "Get a free API key at: https://console.anthropic.com"
read -p "Enter your Anthropic API key: " key
echo "ANTHROPIC_API_KEY=$key" > .env
cat > config.py <<EOF
ANTHROPIC_API_KEY = "$key"
MODEL = "claude-sonnet-5"
AGENT_NAME = "PocketAI"
MAX_TOKENS = 1024
EOF
echo "Starting PocketAI. Your browser chat opens at http://localhost:5001"
echo "Leave this window open while you use PocketAI; press Ctrl+C to stop it."
echo "Prefer the terminal? Stop this and run: python3 agent.py"
(sleep 3; open http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 2>/dev/null) &
POCKETAI_BACKEND=claude python3 server/app.py
