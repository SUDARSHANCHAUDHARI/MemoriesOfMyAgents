# Claude Desktop Integration

Uses MCP server only.

## Install

```bash
bash integrations/claude-desktop/install.sh
```

This writes to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

## Verify

Restart Claude Desktop → open a conversation → the moma tools should appear in the tools panel.

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_memory_forget` — soft-delete a memory
- `moma_session_start` / `moma_session_end` — session lifecycle
- `moma_guardlock_check` — check if action is allowed
