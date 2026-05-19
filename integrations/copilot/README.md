# GitHub Copilot Integration

GitHub Copilot does not expose a hook system or MCP server support.
Memory capture uses the **filesystem watcher** exclusively.

## How to use

Start the watcher in a terminal while Copilot is active in VS Code:

```bash
bash integrations/watcher/install.sh /path/to/your/project
```

The watcher polls `git status` every 5 seconds. When Copilot edits files, it captures them as observations. Stop with Ctrl+C to trigger compression and memory extraction.

## Limitations vs other agents

| Feature | Copilot | Others (Cline, Cursor, etc.) |
|---|---|---|
| Automatic file capture | Yes (via watcher) | Yes (via watcher or hooks) |
| Inject past memories | No | Yes (MCP `moma_context_build`) |
| Save memories on demand | No | Yes (MCP `moma_memory_save`) |
| GuardLock enforcement | No | Yes (MCP `moma_guardlock_check`) |

Copilot is chat-only — it cannot call external tools mid-session.
Memories built from watcher observations will be available to other agents (Claude Code, Cursor, etc.) that share the same `~/.moma/` store.

## Future

GitHub is adding MCP support to Copilot (in preview as of 2025).
Once stable, a full MCP integration will be added here.
