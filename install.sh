#!/usr/bin/env bash
set -e

REPO="https://github.com/dennislysenko/bugsnag-dsym-sync.git"
INSTALL_DIR="$HOME/.local/share/bugsnag-dsym-sync"
BIN_LINK="/usr/local/bin/bugsnag-dsym-sync"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating bugsnag-dsym-sync..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "Installing bugsnag-dsym-sync..."
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

# Check for bugsnag-dsym-upload dependency
if ! command -v bugsnag-dsym-upload &>/dev/null; then
    echo ""
    echo "⚠ bugsnag-dsym-upload not found on PATH (required for uploads)."
    echo "  Install it with: gem install bugsnag-dsym-upload"
fi

echo ""
echo "✓ Installed! Run: bugsnag-dsym-sync"
