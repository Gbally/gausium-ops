#!/bin/bash
# Gausium Ops — Mac launcher
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
  echo "Python 3.10+ is required."
  echo "Install from https://www.python.org or via Homebrew: brew install python"
  exit 1
fi

PY_VER=$(python3 -c "import sys; print(sys.version_info.minor + sys.version_info.major * 10)")
if [ "$PY_VER" -lt 40 ]; then
  echo "Python 3.10+ required. Install from https://www.python.org"
  exit 1
fi

echo "Gausium Ops — checking dependencies…"

# Install deps into a local venv on first run
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (first run only)…"
  python3 -m venv .venv
  echo "Installing dependencies (downloads ~60 MB first time)…"
  .venv/bin/pip install --quiet -r requirements.txt
  echo "Done."
fi

echo "Launching Gausium Ops…"
.venv/bin/python gausium_ops.py
