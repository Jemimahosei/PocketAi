# PocketAI terminal chat (agent.py) settings.
#
# Copy this file to config.py and replace the placeholder with your
# Anthropic API key:
#
#     cp config.example.py config.py
#
# config.py is gitignored — never commit your real key.
# (The web chat, server/app.py, does not need this file.)

ANTHROPIC_API_KEY = "sk-ant-your-key-here"
MODEL = "claude-sonnet-4-5"
AGENT_NAME = "PocketAI"
MAX_TOKENS = 1024
