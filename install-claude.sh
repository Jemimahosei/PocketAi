#!/bin/bash
echo "Installing PocketAI (Claude)..."

# PocketAI needs git, python3 and curl. Say so up front instead of
# failing halfway through the install.
missing=""
for cmd in git python3 curl; do
  command -v $cmd >/dev/null 2>&1 || missing="$missing $cmd"
done
if [ -n "$missing" ]; then
  echo "PocketAI needs these first:$missing"
  echo "On a Mac, 'xcode-select --install' provides git and python3; curl is built in."
  exit 1
fi

# Get or update the code. Re-running the installer must not fail just
# because a file in the folder changed: tracked app files are
# refreshed (config.py is untracked and always kept), and a folder
# that is not a git copy is moved aside, never deleted.
if [ -d ~/PocketAi/.git ]; then
  cd ~/PocketAi
  if ! git pull --ff-only; then
    echo "Your PocketAi folder has changes that block a normal update — refreshing the app files. Your config.py settings are kept."
    git fetch origin && git reset --hard origin/main
  fi
elif [ -d ~/PocketAi ]; then
  mv ~/PocketAi ~/PocketAi-old
  echo "Your old PocketAi folder was moved to ~/PocketAi-old, and a fresh copy was downloaded."
  git clone https://github.com/Jemimahosei/PocketAi.git ~/PocketAi && cd ~/PocketAi
else
  git clone https://github.com/Jemimahosei/PocketAi.git ~/PocketAi && cd ~/PocketAi
fi

# Install the Python packages into PocketAI's own virtual environment.
# Installing into the system Python is refused outright by modern
# setups (Homebrew Python, Debian/Ubuntu — PEP 668), which used to
# leave new users with a server that crashed on missing packages.
if [ ! -x .venv/bin/python ]; then
  if ! python3 -m venv .venv; then
    echo "PocketAI needs Python's venv module to set up its own environment."
    echo "On Ubuntu/Debian: sudo apt install python3-venv — then run this command again."
    exit 1
  fi
fi
if ! .venv/bin/pip install -r requirements.txt; then
  echo "Installing PocketAI's Python packages failed — see the messages above."
  echo "PocketAI isn't installed yet; fix that and run this command again."
  exit 1
fi

# The key lives in exactly one place: config.py, which the terminal
# chat and the server both read. (An earlier version also wrote it to
# a .env file that nothing ever read.)
if [ -f config.py ] && grep -q "ANTHROPIC_API_KEY" config.py && ! grep -q "your-api-key" config.py; then
  echo "Keeping the API key already saved in config.py."
else
  echo "Get an API key at: https://console.anthropic.com"
  read -s -p "Enter your Anthropic API key (typing is hidden): " key
  echo
  cat > config.py <<EOF
ANTHROPIC_API_KEY = "$key"
MODEL = "claude-sonnet-5"
AGENT_NAME = "PocketAI"
MAX_TOKENS = 1024
EOF
fi

echo "Starting PocketAI. Your browser chat opens at http://localhost:5001"
echo "Leave this window open while you use PocketAI; press Ctrl+C to stop it."
echo "Prefer the terminal? Stop this and run: .venv/bin/python agent.py"
(sleep 3; open http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 2>/dev/null) &
POCKETAI_BACKEND=claude .venv/bin/python server/app.py
