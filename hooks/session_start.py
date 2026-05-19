#!/usr/bin/env python3
"""
SessionStart hook — creates session file, no HTTP, no server.
Errors go to stderr only. Never blocks the agent.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, Session, ids
from moma.storage import slugify


def get_git_branch(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_project_name(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).name
    except Exception:
        pass
    return Path(cwd).name


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[moma] session_start: failed to parse input: {e}", file=sys.stderr)
        sys.exit(0)

    session_id = data.get("session_id") or ids.session_id()
    cwd = data.get("cwd") or os.getcwd()

    project = get_project_name(cwd)
    project_slug = slugify(project)
    git_branch = get_git_branch(cwd)
    model = data.get("model", "")
    agent = "claude-code"

    session = Session(
        id=session_id,
        project=project,
        project_slug=project_slug,
        cwd=cwd,
        agent=agent,
        git_branch=git_branch,
        model=model,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        storage = Storage()
        storage.save_session(session)
    except Exception as e:
        print(f"[moma] session_start: failed to save session: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
