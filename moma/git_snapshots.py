"""
Git-versioned snapshots — memory store backed by a real git repo.
Runs git init/add/commit inside ~/.moma/ so every snapshot is a real commit.
Supports rollback to any previous snapshot.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import MOMA_ROOT


def _git(args: list[str], cwd: Path = MOMA_ROOT) -> tuple[int, str]:
    r = subprocess.run(
        ["git"] + args, cwd=str(cwd),
        capture_output=True, text=True
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def _ensure_git_repo() -> bool:
    """Init git repo inside MOMA_ROOT if not already done."""
    if (MOMA_ROOT / ".git").exists():
        return True
    MOMA_ROOT.mkdir(parents=True, exist_ok=True)
    code, _ = _git(["init"])
    if code != 0:
        return False
    # Add .gitignore for embed cache and tmp files
    gitignore = MOMA_ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("index/embed_cache.json\n*.tmp\n")
    _git(["config", "user.email", "moma@localhost"])
    _git(["config", "user.name", "moma"])
    return True


def create_snapshot(label: str = "") -> dict:
    """Commit current state of memories/ index/ to git."""
    if not _ensure_git_repo():
        return {"error": "git not available"}

    ts = datetime.now(timezone.utc).isoformat()
    msg = f"moma snapshot: {label or ts}"

    # Stage only memories and index (not raw/ or sessions/ — too noisy)
    _git(["add", "memories/", "index/", "graph/"])
    code, out = _git(["commit", "-m", msg, "--allow-empty"])

    if code != 0 and "nothing to commit" in out:
        return {"message": "nothing changed since last snapshot", "label": label}

    _, sha = _git(["rev-parse", "HEAD"])
    return {"sha": sha[:12], "label": label, "committed_at": ts, "message": msg}


def list_snapshots(limit: int = 20) -> list[dict]:
    """List recent git commits as snapshots."""
    if not (MOMA_ROOT / ".git").exists():
        return []
    code, out = _git(["log", f"--max-count={limit}", "--format=%H|%s|%ai"])
    if code != 0 or not out:
        return []
    snapshots = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            snapshots.append({"sha": parts[0][:12], "message": parts[1], "committed_at": parts[2].strip()})
    return snapshots


def rollback_snapshot(sha: str) -> dict:
    """Roll back memories to a specific snapshot SHA."""
    if not (MOMA_ROOT / ".git").exists():
        return {"error": "no git repo"}
    # Create a restore commit rather than destructive reset
    code, out = _git(["checkout", sha, "--", "memories/", "index/"])
    if code != 0:
        return {"error": out}
    commit_code, commit_out = _git(["commit", "-m", f"moma rollback to {sha[:8]}", "--allow-empty"])
    return {"rolled_back_to": sha[:12], "message": commit_out}


def diff_snapshots(sha1: str, sha2: str = "HEAD") -> str:
    """Show diff between two snapshots."""
    if not (MOMA_ROOT / ".git").exists():
        return "no git repo"
    _, out = _git(["diff", "--stat", sha1, sha2])
    return out
