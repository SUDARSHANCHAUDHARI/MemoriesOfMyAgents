# Windsurf Integration

Uses MCP server only.

## Install

```bash
bash integrations/windsurf/install.sh
```

Or manually: copy `integrations/windsurf/mcp.json` to `~/.windsurf/mcp.json`.

## Verify

Open Windsurf → Settings → MCP Servers → `moma` should appear with 7 tools.

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_memory_forget` — soft-delete a memory
- `moma_session_start` — register a session
- `moma_session_end` — end session + trigger compression
- `moma_guardlock_check` — check if action is allowed
