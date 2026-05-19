# Claude Code Integration

Installs 5 hooks that capture every session automatically.

## Install

```bash
bash integrations/claude-code/install.sh
```

## What gets installed

| Hook | Event | Does |
|---|---|---|
| `session_start.py` | SessionStart | Creates session file on disk |
| `prompt_submit.py` | UserPromptSubmit | Extracts intent + injects memories |
| `post_tool_use.py` | PostToolUse | Appends tool call to JSONL |
| `pre_tool_use.py` | PreToolUse | Evaluates GuardLocks |
| `stop.py` | Stop | Triggers async compression |

## Verify

Start a Claude Code session, do some work, then check:

```bash
ls ~/.moma/sessions/          # should show a session file
ls ~/.moma/raw/               # should show a JSONL file
cat ~/.moma/index/MEMORY_INDEX.md   # populated after first compression
```

## MCP (optional)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "moma": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/mcp_server/server.py"]
    }
  }
}
```
