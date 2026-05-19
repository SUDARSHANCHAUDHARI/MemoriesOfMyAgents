# Filesystem Watcher

Universal memory capture for any agent that edits files — Cursor, Windsurf, Gemini CLI, Codex, or any tool that modifies a git repo.

## How it works

The watcher polls `git status --porcelain` every 5 seconds. When files change it writes a `RawObservation` directly to `~/.moma/raw/{session_id}.jsonl` — no HTTP, no server, no extra dependencies. When you stop it (Ctrl+C), it fires `compress_session.py` asynchronously to extract memories via Claude Haiku.

## Install / run

```bash
# Start watching a project (from the moma repo root)
bash integrations/watcher/install.sh /path/to/your/project

# Or run directly
python3 scripts/fs_watcher.py /path/to/your/project

# No argument = current directory
python3 scripts/fs_watcher.py
```

## Requirements

- Python 3.10+ (no extra packages — stdlib only)
- The watched directory must be a git repo
- `ANTHROPIC_API_KEY` set for compression (optional — raw observations are still saved without it)

## Typical workflow with Cursor / Windsurf / Gemini CLI

```
Terminal A: your AI agent (Cursor, Windsurf, etc.)
Terminal B: python3 scripts/fs_watcher.py /path/to/project
```

When you finish your session, Ctrl+C in Terminal B. Compression runs in the background and writes memories to `~/.moma/memories/`.

## Auto-detection

The watcher tries to detect which agent is running from environment variables:

| Agent | Env var checked |
|---|---|
| Cursor | `CURSOR_TRACE_ID` |
| Windsurf | `WINDSURF_SESSION_ID` |
| Gemini CLI | `GEMINI_CLI` |
| Codex | `CODEX_SESSION_ID` |
| Fallback | `fs-watcher` |

## Importance scoring

| File type | Importance hint |
|---|---|
| `.kt`, `.swift`, `.ts`, `.tsx`, `.py`, `.go` | 7 |
| `.json`, `.yaml`, `.toml`, `.gradle` | 5 |
| `test*`, `spec*` | 6 |
| Other | 3 |

High-importance observations are prioritised during compression.
