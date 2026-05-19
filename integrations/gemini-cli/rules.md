# MemoriesOfMyAgents — Gemini CLI Rules

## Memory System
You have access to a persistent memory system via the `moma` MCP server.
Use it proactively to capture knowledge across sessions.

## Session Start (always)
At the start of every Gemini CLI session, call:
```
moma_context_build(project="<project-name>", max_memories=10)
```
Read the returned context block before writing any code or answering questions.

## Saving Memories (proactively)
Call `moma_memory_save` whenever you observe or decide something worth remembering:

| When | What to save |
|---|---|
| User corrects your approach | "User prefers X over Y in this codebase" |
| You discover a non-obvious pattern | Architecture decision, invariant, hidden constraint |
| A bug is fixed | Root cause + fix |
| A config value is confirmed | Real value, not assumed |
| User names a deadline or constraint | With absolute date |

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
Before debugging or major changes:
```
moma_memory_search(query="...", project="<project-name>")
```

## GuardLocks
Before destructive operations:
```
moma_guardlock_check(action="...", tool="...", target="...")
```

## Filesystem Capture (recommended)
For automatic capture, start the watcher in a separate terminal:
```bash
python3 /path/to/MemoriesOfMyAgents/scripts/fs_watcher.py /path/to/your/project
```
Ctrl+C to stop — triggers async compression and memory extraction.
