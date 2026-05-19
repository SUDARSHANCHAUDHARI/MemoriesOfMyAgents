#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"

# macOS path for Claude Desktop
CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo "Installing MemoriesOfMyAgents MCP server for Claude Desktop..."

mkdir -p "$(dirname "$CLAUDE_DESKTOP_CONFIG")"

python3 - <<EOF
import json, os

config_path = "$CLAUDE_DESKTOP_CONFIG"
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

config = {}
if os.path.exists(config_path):
    try:
        config = json.loads(open(config_path).read())
    except Exception:
        pass

servers = config.setdefault("mcpServers", {})
servers["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key}
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP config written to {config_path}")
EOF

echo ""
echo "Done. Restart Claude Desktop to activate moma MCP tools."
