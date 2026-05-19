# MemoriesOfMyAgents — Windsurf Rules

## Memory System
You have access to a persistent memory system via the `moma` MCP server.
Use it proactively to build an accurate, evolving picture of this project.

## Session Start (always)
At the start of every Windsurf session or Cascade flow, call:
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
| A bug is fixed | Root cause + fix, not just "fixed" |
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

Save at minimum one memory per session. Cascade flows that produce architectural decisions
should save at least one `architecture` type memory.

## Searching Memory
Before answering questions about past decisions, before debugging, before major changes:
```
moma_memory_search(query="...", project="<project-name>")
```

## GuardLocks
Before destructive operations (delete files, reset branches, drop tables):
```
moma_guardlock_check(action="...", tool="...", target="...")
```
If it returns `block`, stop and explain to the user. If `warn`, proceed with caution.

## Filesystem Capture (recommended)
For automatic memory capture without manual tool calls, run in a terminal:
```bash
python3 /path/to/MemoriesOfMyAgents/scripts/fs_watcher.py /path/to/your/project
```
The watcher polls git every 5 seconds, captures file changes, and compresses them into memories
when you stop it (Ctrl+C). Zero extra dependencies — pure Python stdlib.
