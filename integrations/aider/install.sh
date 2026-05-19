#!/usr/bin/env bash
# Aider doesn't have native session hooks — we install a wrapper script
# that calls moma hooks before/after aider runs.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_DIR/hooks"
WRAPPER="$HOME/.local/bin/moma-aider"

echo "Installing MemoriesOfMyAgents wrapper for Aider..."

mkdir -p "$HOME/.local/bin"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# moma-aider: run aider with moma session lifecycle hooks
HOOKS_DIR="$HOOKS_DIR"
WATCHER="$PROJECT_DIR/scripts/fs_watcher.py"
CWD="\$(pwd)"

# Start session
python3 "\$HOOKS_DIR/session_start.py" 2>/dev/null || true

# Start filesystem watcher in background
python3 "\$WATCHER" "\$CWD" &
WATCHER_PID=\$!

# Run aider with all args passed through
aider "\$@"
EXIT_CODE=\$?

# Stop watcher (triggers compression)
kill \$WATCHER_PID 2>/dev/null || true
wait \$WATCHER_PID 2>/dev/null || true

exit \$EXIT_CODE
EOF

chmod +x "$WRAPPER"
chmod +x "$HOOKS_DIR"/*.py

echo ""
echo "Done. Use 'moma-aider' instead of 'aider':"
echo "  moma-aider --model gpt-4o"
echo "  moma-aider --model claude-opus-4-5"
echo ""
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo "NOTE: Add ~/.local/bin to PATH:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    echo ""
fi
echo "Memories stored at: ~/.moma/"
