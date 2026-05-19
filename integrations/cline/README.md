# Cline Integration

Uses Cline's built-in MCP server support.

## Install

```bash
bash integrations/cline/install.sh
```

Writes the `moma` entry to Cline's MCP settings file:
- macOS: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

## Verify

1. Open VS Code → Cline panel → MCP Servers tab
2. You should see `moma` listed as connected
3. In a chat, ask Cline to call `moma_context_build` for your project

## Rules (optional but recommended)

Add to your project's `.clinerules`:
```bash
cp integrations/cline/rules.md /path/to/project/.clinerules
```

Or via deploy script:
```bash
bash scripts/deploy_rules.sh cline /path/to/your/project
```

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_guardlock_check` — check if action is allowed
- `moma_session_start` / `moma_session_end` — session lifecycle
