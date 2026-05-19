# Codex CLI Integration

Two capture paths — use both for best coverage:

1. **MCP server** — Codex calls moma tools directly when it needs memory
2. **Shell hooks** in `~/.codex/config.toml` — automatic session lifecycle
3. **Filesystem watcher** — automatic capture of all file changes (recommended)

## Install

```bash
bash integrations/codex/install.sh
```

This writes:
- `~/.codex/mcp.json` — MCP server entry
- `~/.codex/config.toml` — session start/end + pre/post exec hooks

## Filesystem watcher (recommended)

Codex hook support varies by version. The watcher is the most reliable capture path:

```bash
# In a separate terminal while Codex is running:
bash integrations/watcher/install.sh /path/to/your/project
# Ctrl+C when done — compression runs automatically
```

## Verify

Start a Codex session, do some work, then:

```bash
ls ~/.moma/sessions/   # session file should appear
ls ~/.moma/raw/        # JSONL observations
```

## Available MCP tools

- `moma_memory_search` — search your memory store
- `moma_context_build` — full project context block
- `moma_memory_save` — save a memory manually
- `moma_guardlock_check` — check if action is allowed
