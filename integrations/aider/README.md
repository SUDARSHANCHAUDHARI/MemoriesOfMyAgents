# Aider Integration

Aider has no native hook system, so moma wraps it via a shell script.

## How it works

`moma-aider` is a thin wrapper around `aider` that:
1. Calls `session_start.py` before aider starts
2. Starts the filesystem watcher in the background (captures all file changes via git polling)
3. Runs `aider` with all your arguments passed through unchanged
4. On exit: kills the watcher → triggers async compression → memories written to `~/.moma/`

## Install

```bash
bash integrations/aider/install.sh
```

Installs `~/.local/bin/moma-aider`.

## Use

```bash
# Drop-in replacement for aider
moma-aider --model gpt-4o
moma-aider --model claude-opus-4-5 --no-auto-commits
moma-aider --watch-files
```

All aider flags work unchanged — moma-aider is purely a wrapper.

## Verify

After a session:

```bash
ls ~/.moma/sessions/   # session JSON
ls ~/.moma/raw/        # file-change observations
ls ~/.moma/memories/   # extracted memories (after compression)
```

## Manual save (inside aider chat)

Aider doesn't support MCP, so memories must be created automatically via compression.
You can also save manually from the terminal after a session:

```bash
python3 /path/to/moma/scripts/compress_session.py <session_id>
```
