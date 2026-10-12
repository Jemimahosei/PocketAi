#!/bin/bash
echo "Installing PocketAI (Claude)..."
if [ -d ~/PocketAi ]; then cd ~/PocketAi && git pull
else git clone https://github.com/Jemimahosei/PocketAi.git ~/PocketAi && cd ~/PocketAi
fi
pip3 install -r requirements.txt
echo "Get a free API key at: https://console.anthropic.com"
read -p "Enter your Anthropic API key: " key
echo "ANTHROPIC_API_KEY=$key" > .env
python3 agent.py
