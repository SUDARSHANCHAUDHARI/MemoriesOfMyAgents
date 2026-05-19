# Roo Code Integration

Uses Roo Code's built-in MCP server support.

## Install

```bash
bash integrations/roo-code/install.sh
```

Writes the `moma` entry to Roo Code's MCP settings file:
- macOS: `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`

## Verify

1. Open VS Code → Roo Code panel → MCP Servers tab
2. You should see `moma` listed as connected
3. Test: ask Roo Code to call `moma_context_build` for your project

## Rules (optional but recommended)

```bash
cp integrations/roo-code/rules.md /path/to/project/.roorules
```

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_guardlock_check` — check if action is allowed
- `moma_session_start` / `moma_session_end` — session lifecycle
