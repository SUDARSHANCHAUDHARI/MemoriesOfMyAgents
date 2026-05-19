#!/usr/bin/env python3
"""
Filesystem watcher — universal capture for ANY agent.
Works for Cursor, Windsurf, Gemini CLI, Codex, or any tool that edits files.

Run:  python3 scripts/fs_watcher.py [project_dir]
Stop: Ctrl+C — automatically triggers compression on exit.

Polls git every 5s. When files change, writes an observation to ~/.moma/raw/.
No extra dependencies — uses only stdlib + git.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR_CODE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR_CODE))

from moma import Storage, RawObservation, Session, ids
from moma.storage import slugify

POLL_INTERVAL = 5  # seconds


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_git(args: list[str], cwd: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=cwd,
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def get_project_name(cwd: str) -> str:
    top = run_git(["rev-parse", "--show-toplevel"], cwd)
    return Path(top).name if top else Path(cwd).name


def get_branch(cwd: str) -> str:
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def get_status(cwd: str) -> str:
    return run_git(["status", "--porcelain"], cwd)


def get_diff_stat(cwd: str) -> str:
    return run_git(["diff", "--stat", "HEAD"], cwd)


def get_changed_files(cwd: str) -> list[str]:
    out = run_git(["status", "--porcelain"], cwd)
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def detect_agent() -> str:
    """Best-effort: detect which agent is likely running."""
    env = os.environ
    if env.get("CURSOR_TRACE_ID"): return "cursor"
    if env.get("WINDSURF_SESSION_ID"): return "windsurf"
    if env.get("GEMINI_CLI"): return "gemini-cli"
    if env.get("CODEX_SESSION_ID"): return "codex"
    return "fs-watcher"


def main():
    cwd = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    cwd = str(Path(cwd).resolve())

    if not Path(cwd).exists():
        print(f"[moma-watcher] ERROR: {cwd} does not exist", file=sys.stderr)
        sys.exit(1)

    project = get_project_name(cwd)
    project_slug = slugify(project)
    agent = detect_agent()
    session_id = ids.session_id()

    storage = Storage()
    storage.init()

    # Register session
    session = Session(
        id=session_id,
        project=project,
        project_slug=project_slug,
        cwd=cwd,
        agent=agent,
        git_branch=get_branch(cwd),
        started_at=now(),
    )
    storage.save_session(session)

    print(f"[moma-watcher] watching {cwd}", file=sys.stderr)
    print(f"[moma-watcher] session {session_id} | agent: {agent}", file=sys.stderr)
    print(f"[moma-watcher] Ctrl+C to stop and compress", file=sys.stderr)

    last_status = get_status(cwd)
    last_hash = hashlib.sha256(last_status.encode()).hexdigest()
    obs_count = 0

    def on_stop(sig, frame):
        print(f"\n[moma-watcher] stopping — {obs_count} observations captured", file=sys.stderr)
        storage.end_session(session_id)
        compress = PROJECT_DIR_CODE / "scripts" / "compress_session.py"
        if compress.exists():
            subprocess.Popen(
                [sys.executable, str(compress), session_id],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            print(f"[moma-watcher] compression triggered for {session_id}", file=sys.stderr)
        sys.exit(0)

    signal.signal(signal.SIGINT, on_stop)
    signal.signal(signal.SIGTERM, on_stop)

    while True:
        time.sleep(POLL_INTERVAL)

        status = get_status(cwd)
        current_hash = hashlib.sha256(status.encode()).hexdigest()

        if current_hash == last_hash:
            continue

        # Files changed — record observation
        changed_files = get_changed_files(cwd)
        diff_stat = get_diff_stat(cwd)

        # Determine importance from file types
        importance = 3
        for f in changed_files:
            if any(f.endswith(ext) for ext in [".kt", ".swift", ".ts", ".tsx", ".py", ".go"]):
                importance = max(importance, 7)
            elif any(f.endswith(ext) for ext in [".json", ".yaml", ".toml", ".gradle"]):
                importance = max(importance, 5)
            elif "test" in f.lower() or "spec" in f.lower():
                importance = max(importance, 6)

        output_tail = f"Changed files:\n{status}\n\nDiff stat:\n{diff_stat}"

        obs = RawObservation(
            id=ids.observation_id(),
            session_id=session_id,
            timestamp=now(),
            tool="file_change",
            tool_input_hash=current_hash[:16],
            output_tail=output_tail[-4000:],  # last 4000 chars
            importance_hint=importance,
        )

        try:
            storage.append_observation(obs)
            obs_count += 1
            print(
                f"[moma-watcher] change detected: {len(changed_files)} files "
                f"(obs #{obs_count})",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[moma-watcher] ERROR writing obs: {e}", file=sys.stderr)

        last_hash = current_hash


if __name__ == "__main__":
    main()
