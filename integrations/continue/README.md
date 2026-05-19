# Continue.dev Integration

Uses MCP server. Works in VS Code and JetBrains.

## Install

```bash
bash integrations/continue/install.sh
```

Writes `moma` entry to `~/.continue/config.json`.

## Verify

1. Reload the Continue extension in VS Code / JetBrains
2. Open a chat → type `@moma` — you should see the moma tools listed

## Add rules to your project

```bash
bash scripts/deploy_rules.sh continue /path/to/your/project
# Creates .continuerules in the project root
```

Or copy manually:
```bash
cp integrations/continue/rules.md /path/to/project/.continuerules
```

## Available tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_guardlock_check` — check if action is allowed
