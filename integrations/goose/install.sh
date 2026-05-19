#!/usr/bin/env bash
# Goose (Block's open-source agent) — MCP server integration
# Goose reads MCP servers from ~/.config/goose/config.yaml
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"
GOOSE_CONFIG="$HOME/.config/goose/config.yaml"

echo "Installing MemoriesOfMyAgents MCP server for Goose..."

mkdir -p "$HOME/.config/goose"

python3 - <<EOF
import os, sys, re

config_path = os.path.expanduser("$GOOSE_CONFIG")
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

moma_block = f"""
# MemoriesOfMyAgents MCP server
extensions:
  moma:
    type: stdio
    cmd: {venv_python}
    args:
      - {mcp_server}
    env:
      ANTHROPIC_API_KEY: "{api_key}"
"""

if os.path.exists(config_path):
    content = open(config_path).read()
    if "MemoriesOfMyAgents" in content:
        print("  moma already in ~/.config/goose/config.yaml")
        sys.exit(0)
    content += moma_block
else:
    content = moma_block.lstrip()

with open(config_path, "w") as f:
    f.write(content)
print(f"  MCP config written to {config_path}")
EOF

echo ""
echo "Done. Restart Goose to activate moma tools."
echo "Memories stored at: ~/.moma/"
