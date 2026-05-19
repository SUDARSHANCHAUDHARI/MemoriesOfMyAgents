#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"
CONTINUE_CONFIG="$HOME/.continue/config.json"

echo "Installing MemoriesOfMyAgents MCP server for Continue.dev..."

mkdir -p "$HOME/.continue"

python3 - <<EOF
import json, os

config_path = os.path.expanduser("~/.continue/config.json")
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

config = {}
if os.path.exists(config_path):
    try:
        config = json.loads(open(config_path).read())
    except Exception:
        pass

# Continue uses a list for mcpServers
servers = config.setdefault("mcpServers", [])

# Remove existing moma entry if present
servers = [s for s in servers if s.get("name") != "moma"]

servers.append({
    "name": "moma",
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key}
})

config["mcpServers"] = servers

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP server written to {config_path}")
EOF

echo ""
echo "Done. Reload the Continue extension in VS Code / JetBrains."
echo ""
echo "Available tools: moma_memory_search, moma_context_build, moma_memory_save, moma_guardlock_check"
echo "Memories stored at: ~/.moma/"
