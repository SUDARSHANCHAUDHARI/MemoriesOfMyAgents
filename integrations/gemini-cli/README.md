# Gemini CLI Integration

Uses MCP server only.

## Install

```bash
bash integrations/gemini-cli/install.sh
```

Or manually: copy `integrations/gemini-cli/mcp.json` to `~/.gemini/mcp.json`.

## Verify

Run `gemini` → the moma MCP tools should be available.

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_guardlock_check` — check if action is allowed
