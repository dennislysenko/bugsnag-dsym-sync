#!/usr/bin/env bash
# Resolve symlinks to find the real script directory
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
VENV="$SCRIPT_DIR/venv"
if [ ! -d "$VENV" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
fi
exec "$VENV/bin/python" "$SCRIPT_DIR/bugsnag-upload.py" "$@"
