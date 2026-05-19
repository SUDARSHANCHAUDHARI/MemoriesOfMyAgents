#!/usr/bin/env python3
"""
PostToolUseFailure hook — captures tool failures as high-importance observations.
Failures are the most valuable signals: they reveal hidden constraints and bugs.
"""
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, RawObservation, ids
from moma.privacy import scrub

ACTIVE_SESSION_FILE = Path.home() / ".moma" / "active_session.json"


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    tool_name = data.get("tool_name", "unknown")
    error = data.get("error", data.get("tool_response", ""))
    if isinstance(error, dict):
        error = json.dumps(error)

    # Get active session
    if not ACTIVE_SESSION_FILE.exists():
        sys.exit(0)
    try:
        session_id = json.loads(ACTIVE_SESSION_FILE.read_text()).get("session_id", "")
    except Exception:
        sys.exit(0)

    if not session_id:
        sys.exit(0)

    # Failures always get importance 9 — they expose real constraints
    output_tail = scrub(f"TOOL FAILURE: {tool_name}\nError: {str(error)[-3000:]}")

    obs = RawObservation(
        id=ids.observation_id(),
        session_id=session_id,
        timestamp=now(),
        tool=f"FAIL:{tool_name}",
        tool_input_hash="",
        output_tail=output_tail,
        importance_hint=9,
    )

    try:
        storage = Storage()
        storage.append_observation(obs)
    except Exception as e:
        print(f"[moma] post_tool_use_failure: ERROR: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
