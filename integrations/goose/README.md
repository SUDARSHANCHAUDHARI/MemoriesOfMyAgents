# Goose Integration

Block's open-source AI agent. Supports MCP via `~/.config/goose/config.yaml`.

## Install

```bash
bash integrations/goose/install.sh
```

## Verify

```bash
goose session start
# In the session, call: moma_context_build(project="myproject")
```

## Available tools (20)

All 20 moma MCP tools available. See Kilo Code README for full list.

## Filesystem watcher (recommended)

Since Goose doesn't have automatic hooks, also run the watcher:

```bash
bash integrations/watcher/install.sh /path/to/your/project
```
