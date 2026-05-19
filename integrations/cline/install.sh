#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"

# Cline stores MCP config in its own settings file
CLINE_MCP="$HOME/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"

echo "Installing MemoriesOfMyAgents MCP server for Cline..."

python3 - <<EOF
import json, os

settings_path = os.path.expandvars(
    os.path.expanduser("$CLINE_MCP")
)
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

# Try macOS path, fall back to Linux
if not os.path.exists(os.path.dirname(settings_path)):
    settings_path = os.path.expanduser(
        "~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
    )

os.makedirs(os.path.dirname(settings_path), exist_ok=True)

config = {"mcpServers": {}}
if os.path.exists(settings_path):
    try:
        config = json.loads(open(settings_path).read())
    except Exception:
        pass

servers = config.setdefault("mcpServers", {})
servers["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key},
    "disabled": False,
    "autoApprove": []
}

with open(settings_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP config written to {settings_path}")
EOF

echo ""
echo "Done. Reload VS Code or click 'Restart MCP Server' in the Cline panel."
echo ""
echo "Available tools: moma_memory_search, moma_context_build, moma_memory_save, moma_guardlock_check"
echo "Memories stored at: ~/.moma/"
