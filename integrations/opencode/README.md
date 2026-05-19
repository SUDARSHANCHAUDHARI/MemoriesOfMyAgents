# OpenCode Integration

Full integration: 7 hooks + 20 MCP tools.

## Install

```bash
bash integrations/opencode/install.sh
```

Writes to `~/.config/opencode/config.json`.

## What gets installed

**Hooks:**
- `session:start` → session_start.py
- `prompt:submit` → prompt_submit.py (intent extraction + memory injection)
- `tool:post` → post_tool_use.py (capture)
- `tool:post:error` → post_tool_use_failure.py (failure capture, importance=9)
- `tool:pre` → pre_tool_use.py (GuardLocks)
- `compact:pre` → pre_compact.py (context snapshot)
- `session:end` → stop.py (async compression)

**MCP:** 20 tools including search, save, context build, audit log, snapshots, provenance.

## Verify

```bash
ls ~/.moma/sessions/   # session appears on start
ls ~/.moma/raw/        # observations captured per tool use
ls ~/.moma/memories/   # memories after compression
```
