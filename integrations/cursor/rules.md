# MemoriesOfMyAgents — Cursor Rules

## Memory System
You have access to a persistent memory system via the `moma` MCP server.
Use it proactively to build an accurate, evolving picture of this project.

## Session Start (always)
At the start of every session, call:
```
moma_context_build(project="<project-name>", max_memories=10)
```
Read the returned context block before writing any code or answering questions.
This gives you: past decisions, known bugs, architecture patterns, and preferences.

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

## What NOT to save
- Temporary state, in-progress work, "I just did X"
- Things derivable from reading the current code
- Git history (use git log)
- Vague observations without actionable content

## Filesystem Capture (recommended)
For automatic memory capture, start the moma filesystem watcher in the terminal:
```bash
python3 /path/to/MemoriesOfMyAgents/scripts/fs_watcher.py /path/to/your/project
```
Leave it running while Cursor works. It detects file changes via git and writes observations automatically.
Stop with Ctrl+C — triggers compression and memory extraction.
