#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv"
if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
fi
exec "$VENV/bin/python" "$SCRIPT_DIR/bugsnag-upload.py" "$@"
