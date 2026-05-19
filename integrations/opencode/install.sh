#!/usr/bin/env bash
# OpenCode — hooks + MCP integration
# OpenCode reads hooks from ~/.config/opencode/config.json
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_DIR/hooks"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
MCP_SERVER="$PROJECT_DIR/mcp_server/server.py"
OC_CONFIG="$HOME/.config/opencode/config.json"

echo "Installing MemoriesOfMyAgents for OpenCode..."

chmod +x "$HOOKS_DIR"/*.py
mkdir -p "$HOME/.config/opencode"

python3 - <<EOF
import json, os, sys

config_path = os.path.expanduser("$OC_CONFIG")
python = sys.executable
hooks_dir = "$HOOKS_DIR"
venv_python = "$VENV_PYTHON"
mcp_server = "$MCP_SERVER"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")

config = {}
if os.path.exists(config_path):
    try:
        config = json.loads(open(config_path).read())
    except Exception:
        pass

# MCP server
servers = config.setdefault("mcpServers", {})
servers["moma"] = {
    "command": venv_python,
    "args": [mcp_server],
    "env": {"ANTHROPIC_API_KEY": api_key},
}

# Hooks (OpenCode hook format)
hooks = config.setdefault("hooks", {})

def set_hook(event, cmd):
    existing = hooks.get(event, [])
    if cmd not in existing:
        existing.append(cmd)
    hooks[event] = existing

set_hook("session:start",   f"{python} {hooks_dir}/session_start.py")
set_hook("prompt:submit",   f"{python} {hooks_dir}/prompt_submit.py")
set_hook("tool:post",       f"{python} {hooks_dir}/post_tool_use.py")
set_hook("tool:post:error", f"{python} {hooks_dir}/post_tool_use_failure.py")
set_hook("tool:pre",        f"{python} {hooks_dir}/pre_tool_use.py")
set_hook("compact:pre",     f"{python} {hooks_dir}/pre_compact.py")
set_hook("session:end",     f"{python} {hooks_dir}/stop.py")

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"  config written to {config_path}")
EOF

echo ""
echo "Done. OpenCode integration installed:"
echo "  7 hooks + MCP server (20 tools)"
echo "Memories stored at: ~/.moma/"
