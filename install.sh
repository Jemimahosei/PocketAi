#!/bin/bash
echo "Installing PocketAI (free, local Llama 3)..."

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

if ! command -v ollama &> /dev/null; then
  curl -fsSL https://ollama.ai/install.sh | sh
fi
ollama pull llama3.2

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
echo "Starting PocketAI. Your browser chat opens at http://localhost:5001"
echo "Leave this window open while you use PocketAI; press Ctrl+C to stop it."
(sleep 3; open http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 2>/dev/null) &
.venv/bin/python server/app.py
