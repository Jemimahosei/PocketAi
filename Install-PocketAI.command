#!/bin/bash
# PocketAI installer for macOS — double-click this file.
# It runs the full setup (Ollama, the Llama 3.2 model, and PocketAI's
# Python pieces), then opens the PocketAI chat in this window.
cd "$(dirname "$0")"
./install.sh
echo
echo "PocketAI has finished. You can close this window."
