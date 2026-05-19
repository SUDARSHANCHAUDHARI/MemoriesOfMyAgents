# MemoriesOfMyAgents — Cline Rules

## Memory System
You have access to a persistent memory system via the `moma` MCP server.
Use it proactively to capture and recall knowledge across sessions.

## Session Start (always)
At the start of every task, call:
```
moma_context_build(project="<project-name>", max_memories=10)
```
Read the returned block before writing code.

## During the task — save proactively
Call `moma_memory_save` whenever you observe something worth keeping:

| When | What to save |
|---|---|
| User corrects your approach | Preference + reason |
| Non-obvious architecture decision | Decision + tradeoff |
| Bug root cause found | Root cause + fix |
| Config value confirmed | Real value |
| Deadline or constraint | Absolute date |

```
moma_memory_save(
  title="...",
  content="...",
  type="preference|architecture|bug|workflow|fact",
  scope="project|global",
  importance=1-10,
  concepts=["tag1", "tag2"]
)
```

## Before debugging
```
moma_memory_search(query="...", project="<project-name>")
```

## Before destructive operations
```
moma_guardlock_check(action="...", tool="...", target="...")
```
`block` → stop. `warn` → proceed with caution.

## Session end
```
moma_session_end(session_id="<current-session-id>")
```
