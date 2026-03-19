#!/usr/bin/env bash
# AWS FinOps Dashboard — macOS / Linux Launcher

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON=""

# Find python3
if command -v python3 &>/dev/null; then
  PYTHON="python3"
elif command -v python &>/dev/null; then
  PYTHON="python"
else
  echo "ERROR: Python 3 not found. Please install Python 3.8+."
  exit 1
fi

echo ""
echo "  AWS FinOps Dashboard"
echo "  ─────────────────────────────────────"

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  echo "  Creating virtual environment..."
  $PYTHON -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# Install / upgrade dependencies silently
echo "  Checking dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo "  Starting server at http://localhost:5100"
echo "  Press Ctrl+C to stop."
echo ""

python "$SCRIPT_DIR/app.py"
