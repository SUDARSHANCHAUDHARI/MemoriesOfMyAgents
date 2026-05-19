#!/usr/bin/env python3
"""
UserPromptSubmit hook — two jobs:
1. First prompt only: extract session intent, save to session file.
2. First prompt only: inject relevant memories as context (always-on, no env flag).
Subsequent prompts: pass through immediately.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage
from moma.storage import slugify
from moma.config import load as load_config

# Import search using absolute path — hook is called from any cwd
_search = PROJECT_DIR / "scripts" / "search_memories.py"
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("search_memories", str(_search))
_mod = _ilu.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_mod)  # type: ignore
get_relevant_memories = _mod.get_relevant_memories
format_context = _mod.format_context


TASK_TYPE_PATTERNS = {
    "bugfix": r"\b(fix|bug|crash|error|broken|issue|problem|debug)\b",
    "feature": r"\b(add|implement|build|create|new|feature)\b",
    "refactor": r"\b(refactor|clean|improve|restructure|reorganize)\b",
    "hotfix": r"\b(urgent|hotfix|critical|production|prod)\b",
    "review": r"\b(review|check|audit|look at|inspect)\b",
}


def extract_intent(prompt: str, cwd: str) -> dict:
    prompt_lower = prompt.lower()

    task_type = "general"
    for t, pattern in TASK_TYPE_PATTERNS.items():
        if re.search(pattern, prompt_lower):
            task_type = t
            break

    # Extract mentioned files (paths with / or . in them)
    files_mentioned = re.findall(r"[\w./\-]+\.\w{1,6}", prompt)

    # Best-effort domain from keywords
    domain = ""
    domain_hints = {
        "auth": r"\b(auth|login|jwt|token|session|permission)\b",
        "database": r"\b(db|database|sql|room|migration|schema)\b",
        "ui": r"\b(ui|screen|compose|layout|design|view)\b",
        "network": r"\b(api|network|http|request|endpoint|retrofit|ktor)\b",
        "build": r"\b(build|gradle|ci|deploy|release|publish)\b",
    }
    for d, pattern in domain_hints.items():
        if re.search(pattern, prompt_lower):
            domain = d
            break

    return {
        "raw": prompt[:500],
        "task_type": task_type,
        "domain": domain,
        "files_mentioned": files_mentioned[:10],
        "goal": prompt[:200],
    }


def get_recent_files(cwd: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()][:10]
    except Exception:
        pass
    return []


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[moma] prompt_submit: failed to parse input: {e}", file=sys.stderr)
        sys.exit(0)

    session_id = data.get("session_id", "")
    prompt = data.get("prompt", "")
    cwd = data.get("cwd") or os.getcwd()

    if not prompt or not session_id:
        sys.exit(0)

    storage = Storage()
    config = load_config()
    session = storage.load_session(session_id)

    # Only process first prompt (intent not yet set)
    if session and session.get("intent"):
        sys.exit(0)

    # Extract intent
    intent = extract_intent(prompt, cwd)

    # Save intent to session
    if session:
        session["intent"] = intent
        session_path = storage.root / "sessions" / f"{session_id}.json"
        tmp = session_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(session, indent=2))
        tmp.replace(session_path)

    # Inject relevant memories (always-on)
    if not config["injection"]["enabled"]:
        sys.exit(0)

    project_slug = session.get("project_slug", slugify(Path(cwd).name)) if session else slugify(Path(cwd).name)
    project_name = session.get("project", Path(cwd).name) if session else Path(cwd).name
    recent_files = get_recent_files(cwd)
    max_tokens = config["injection"]["max_tokens"]

    try:
        memories = get_relevant_memories(
            query=prompt,
            project_slug=project_slug,
            project_files=recent_files,
            max_tokens=max_tokens,
        )
        if memories:
            context = format_context(memories, project_name)
            # Output as injected context block — Claude Code reads this from stdout
            print(context)
    except Exception as e:
        print(f"[moma] prompt_submit: injection failed: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
