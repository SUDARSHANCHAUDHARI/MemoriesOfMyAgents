#!/usr/bin/env bash
# Install the moma filesystem watcher for any project directory.
# Usage: bash integrations/watcher/install.sh [project_dir]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WATCHER="$PROJECT_DIR/scripts/fs_watcher.py"
TARGET_DIR="${1:-$(pwd)}"

if [ ! -f "$WATCHER" ]; then
    echo "ERROR: watcher not found at $WATCHER" >&2
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "ERROR: target directory does not exist: $TARGET_DIR" >&2
    exit 1
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

# Detect python3
PYTHON="python3"
if command -v python3.13 &>/dev/null; then
    PYTHON="python3.13"
fi

echo "moma filesystem watcher"
echo "  project : $TARGET_DIR"
echo "  python  : $PYTHON"
echo "  Press Ctrl+C to stop — compression runs automatically on exit."
echo ""

exec "$PYTHON" "$WATCHER" "$TARGET_DIR"
