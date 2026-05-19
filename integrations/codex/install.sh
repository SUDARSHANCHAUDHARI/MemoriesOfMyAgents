#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_DIR/hooks"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"
CODEX_CONFIG="$HOME/.codex/config.toml"

echo "Installing MemoriesOfMyAgents for Codex CLI..."
echo "  Step 1: MCP server (primary)"
echo "  Step 2: shell hooks in ~/.codex/config.toml (supplemental)"
echo ""

chmod +x "$HOOKS_DIR"/*.py

mkdir -p "$HOME/.codex"

python3 - <<EOF
import json, os, sys

# ── MCP server entry ──────────────────────────────────────────────
# Codex reads mcpServers from ~/.codex/config.json (JSON, not TOML)
mcp_json_path = os.path.expanduser("~/.codex/mcp.json")
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

config = {}
if os.path.exists(mcp_json_path):
    try:
        config = json.loads(open(mcp_json_path).read())
    except Exception:
        pass

servers = config.setdefault("mcpServers", {})
servers["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key}
}

with open(mcp_json_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  MCP config written to {mcp_json_path}")
EOF

# ── Shell hooks (TOML) ────────────────────────────────────────────
python3 - <<EOF
import os, sys

config_path = os.path.expanduser("~/.codex/config.toml")
python = sys.executable
hooks_dir = "$HOOKS_DIR"

moma_block = (
    "\n# MemoriesOfMyAgents hooks\n"
    "[hooks]\n"
    f'session_start = "{python} {hooks_dir}/session_start.py"\n'
    f'pre_exec      = "{python} {hooks_dir}/pre_tool_use.py"\n'
    f'post_exec     = "{python} {hooks_dir}/post_tool_use.py"\n'
    f'session_end   = "{python} {hooks_dir}/stop.py"\n'
)

if os.path.exists(config_path):
    content = open(config_path).read()
    if "MemoriesOfMyAgents" in content:
        print("  hooks already present in ~/.codex/config.toml")
        sys.exit(0)
    content += moma_block
else:
    content = moma_block.lstrip()

with open(config_path, "w") as f:
    f.write(content)
print(f"  hooks written to {config_path}")
EOF

echo ""
echo "Done. Codex CLI integration installed."
echo ""
echo "For automatic capture (recommended), also run the filesystem watcher:"
echo "  bash integrations/watcher/install.sh /path/to/your/project"
echo ""
echo "Memories stored at: ~/.moma/"
