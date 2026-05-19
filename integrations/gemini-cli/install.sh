#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"
GEMINI_MCP="$HOME/.gemini/mcp.json"

echo "Installing MemoriesOfMyAgents MCP server for Gemini CLI..."

mkdir -p "$HOME/.gemini"

python3 - <<EOF
import json, os

mcp_path = os.path.expanduser("~/.gemini/mcp.json")
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

config = {}
if os.path.exists(mcp_path):
    try:
        config = json.loads(open(mcp_path).read())
    except Exception:
        pass

servers = config.setdefault("mcpServers", {})
servers["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key}
}

with open(mcp_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP config written to {mcp_path}")
EOF

echo ""
echo "Done. Restart Gemini CLI to activate moma MCP tools."
