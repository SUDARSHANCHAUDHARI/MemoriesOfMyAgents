# MemoriesOfMyAgents — Continue.dev Rules

## Memory System
You have access to a persistent memory system via the `moma` MCP server.
Use it proactively to capture and recall knowledge across sessions.

## Session Start (always)
At the start of every conversation, call:
```
moma_context_build(project="<project-name>", max_memories=10)
```
Read the returned block before writing code or answering questions about past decisions.

## Saving Memories (proactively)
Call `moma_memory_save` whenever you observe something worth keeping:

| When | What to save |
|---|---|
| User corrects your approach | "User prefers X over Y in this codebase" |
| Non-obvious architecture discovered | Decision + reason |
| Bug root cause found | Root cause + fix, not just "fixed" |
| Config value confirmed | Real value, not assumed |
| Deadline or constraint mentioned | With absolute date |

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

## Searching Memory
Before debugging or major refactors:
```
moma_memory_search(query="...", project="<project-name>")
```

## GuardLocks
Before destructive operations:
```
moma_guardlock_check(action="...", tool="...", target="...")
```
`block` → stop and explain. `warn` → proceed with caution.
