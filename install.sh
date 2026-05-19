#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo ""
echo "MemoriesOfMyAgents — Installer"
echo "================================"
echo ""

# 1. Python check
if ! command -v python3.13 &>/dev/null && ! command -v python3.12 &>/dev/null && ! command -v python3.11 &>/dev/null; then
    echo "ERROR: Python 3.11+ required. Install via: brew install python"
    exit 1
fi

PYTHON=$(command -v python3.13 || command -v python3.12 || command -v python3.11)
echo "  Python: $PYTHON"

# 2. Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtualenv..."
    $PYTHON -m venv "$VENV_DIR"
fi

# 3. Install MCP into venv
echo "  Installing MCP package..."
"$VENV_DIR/bin/pip" install mcp --quiet

# 4. Setup ~/.moma/
echo "  Initialising ~/.moma/..."
"$VENV_DIR/bin/python3" - <<EOF
import sys
sys.path.insert(0, "$PROJECT_DIR")
from moma import Storage
from moma.config import load as load_config, save as save_config
s = Storage()
s.init()
cfg = load_config()
save_config(cfg)
print("  ~/.moma/ ready")
EOF

# 5. Patch MCP config files with real paths
echo "  Patching integration configs..."
VENV_PYTHON="$VENV_DIR/bin/python3"
for mcp_file in "$PROJECT_DIR"/integrations/*/mcp.json; do
    python3 - <<EOF
import json, re
path = "$mcp_file"
venv = "$VENV_PYTHON"
server = "$PROJECT_DIR/mcp_server/server.py"
with open(path) as f:
    content = f.read()
content = content.replace("REPLACE_WITH_VENV_PYTHON", venv)
content = content.replace("REPLACE_WITH_PROJECT_PATH", "$PROJECT_DIR")
with open(path, "w") as f:
    f.write(content)
EOF
done

# 6. Ask which agents to wire
echo ""
echo "Which agents do you want to install hooks/MCP for?"
echo "  1) Claude Code (hooks + MCP)"
echo "  2) Cursor (MCP only)"
echo "  3) Windsurf (MCP only)"
echo "  4) Gemini CLI (MCP only)"
echo "  5) Claude Desktop (MCP only)"
echo "  6) All of the above"
echo ""
read -rp "Enter numbers separated by space (e.g. 1 3): " choices

install_claude_code() {
    echo "  Installing Claude Code hooks..."
    bash "$PROJECT_DIR/integrations/claude-code/install.sh"
}
install_cursor() {
    echo "  Installing Cursor MCP..."
    mkdir -p "$HOME/.cursor"
    cp "$PROJECT_DIR/integrations/cursor/mcp.json" "$HOME/.cursor/mcp.json"
    echo "  Written to ~/.cursor/mcp.json"
}
install_windsurf() {
    echo "  Installing Windsurf MCP..."
    bash "$PROJECT_DIR/integrations/windsurf/install.sh"
}
install_gemini() {
    echo "  Installing Gemini CLI MCP..."
    bash "$PROJECT_DIR/integrations/gemini-cli/install.sh"
}
install_claude_desktop() {
    echo "  Installing Claude Desktop MCP..."
    bash "$PROJECT_DIR/integrations/claude-desktop/install.sh"
}

for choice in $choices; do
    case $choice in
        1) install_claude_code ;;
        2) install_cursor ;;
        3) install_windsurf ;;
        4) install_gemini ;;
        5) install_claude_desktop ;;
        6)
            install_claude_code
            install_cursor
            install_windsurf
            install_gemini
            install_claude_desktop
            ;;
    esac
done

echo ""
echo "Done."
echo ""
echo "  Memory store:  ~/.moma/"
echo "  Dashboard:     cd $PROJECT_DIR/dashboard && pnpm dev"
echo "  MCP server:    $VENV_PYTHON $PROJECT_DIR/mcp_server/server.py"
echo ""
echo "Set ANTHROPIC_API_KEY to enable session compression."
echo ""
