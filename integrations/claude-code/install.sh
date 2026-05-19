#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$PROJECT_DIR/hooks"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

echo "Installing MemoriesOfMyAgents hooks for Claude Code..."
echo "Project: $PROJECT_DIR"

# Make hooks executable
chmod +x "$HOOKS_DIR"/*.py

# Read existing settings or start fresh
if [ -f "$CLAUDE_SETTINGS" ]; then
    existing=$(cat "$CLAUDE_SETTINGS")
else
    existing="{}"
fi

# Write updated settings with moma hooks
python3 - <<EOF
import json, sys

with open("$CLAUDE_SETTINGS") as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})

def add_hook(event, command, matcher=None):
    entries = hooks.setdefault(event, [])
    entry = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        entry["matcher"] = matcher
    # Avoid duplicates
    for e in entries:
        if e.get("hooks", [{}])[0].get("command") == command:
            return
    entries.append(entry)

python = sys.executable
hooks_dir = "$HOOKS_DIR"

add_hook("SessionStart",        f"{python} {hooks_dir}/session_start.py")
add_hook("UserPromptSubmit",    f"{python} {hooks_dir}/prompt_submit.py")
add_hook("PostToolUse",         f"{python} {hooks_dir}/post_tool_use.py")
add_hook("PostToolUseFailure",  f"{python} {hooks_dir}/post_tool_use_failure.py")
add_hook("PreToolUse",          f"{python} {hooks_dir}/pre_tool_use.py")
add_hook("PreCompact",          f"{python} {hooks_dir}/pre_compact.py")
add_hook("SubagentStart",       f"{python} {hooks_dir}/subagent_start.py")
add_hook("SubagentStop",        f"{python} {hooks_dir}/subagent_stop.py")
add_hook("Stop",                f"{python} {hooks_dir}/stop.py")

with open("$CLAUDE_SETTINGS", "w") as f:
    json.dump(settings, f, indent=2)

settings_path = "$CLAUDE_SETTINGS"
print(f"  hooks written to {settings_path}")
EOF

echo ""
echo "Done. Hooks active for Claude Code (9 hooks):"
echo "  SessionStart       → session_start.py"
echo "  UserPromptSubmit   → prompt_submit.py (intent + injection)"
echo "  PostToolUse        → post_tool_use.py (capture)"
echo "  PostToolUseFailure → post_tool_use_failure.py (failure capture, importance=9)"
echo "  PreToolUse         → pre_tool_use.py (GuardLocks)"
echo "  PreCompact         → pre_compact.py (context snapshot)"
echo "  SubagentStart      → subagent_start.py"
echo "  SubagentStop       → subagent_stop.py"
echo "  Stop               → stop.py (async compression)"
echo ""
echo "Memories stored at: ~/.moma/"
echo "Set ANTHROPIC_API_KEY to enable compression."
