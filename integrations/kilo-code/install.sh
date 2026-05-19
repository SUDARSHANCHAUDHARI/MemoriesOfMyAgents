#!/usr/bin/env bash
# Kilo Code (VS Code extension) — MCP server integration
# Kilo Code uses the same MCP config format as Cline (same extension lineage)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"

KILO_MCP_MAC="$HOME/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/cline_mcp_settings.json"
KILO_MCP_LINUX="$HOME/.config/Code/User/globalStorage/kilocode.kilo-code/settings/cline_mcp_settings.json"

echo "Installing MemoriesOfMyAgents MCP server for Kilo Code..."

python3 - <<EOF
import json, os

mac_path = os.path.expanduser("$KILO_MCP_MAC")
linux_path = os.path.expanduser("$KILO_MCP_LINUX")
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

settings_path = mac_path if os.path.exists(os.path.dirname(mac_path)) else linux_path
os.makedirs(os.path.dirname(settings_path), exist_ok=True)

config = {"mcpServers": {}}
if os.path.exists(settings_path):
    try:
        config = json.loads(open(settings_path).read())
    except Exception:
        pass

config.setdefault("mcpServers", {})["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key},
    "disabled": False,
    "autoApprove": [],
}

with open(settings_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP config written to {settings_path}")
EOF

echo ""
echo "Done. Reload VS Code or click 'Restart MCP Server' in Kilo Code panel."
echo "Memories stored at: ~/.moma/"
