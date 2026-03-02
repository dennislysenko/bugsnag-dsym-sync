#!/usr/bin/env bash
set -e

REPO="https://github.com/dennislysenko/bugsnag-upload.git"
INSTALL_DIR="$HOME/.local/share/bugsnag-upload"
BIN_LINK="/usr/local/bin/bugsnag-upload"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating bugsnag-upload..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "Installing bugsnag-upload..."
    git clone "$REPO" "$INSTALL_DIR"
fi

# Bootstrap venv (run.sh does this on first run, but do it now so install feels complete)
VENV="$INSTALL_DIR/venv"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
fi

# Symlink into PATH
if [ -L "$BIN_LINK" ] || [ -e "$BIN_LINK" ]; then
    rm "$BIN_LINK"
fi
ln -s "$INSTALL_DIR/run.sh" "$BIN_LINK"
chmod +x "$INSTALL_DIR/run.sh"

echo ""
echo "✓ Installed! Run: bugsnag-upload"
