#!/usr/bin/env python3
"""
SubagentStop hook — fires when a subagent (Task tool) completes.
Records outcome for compression — did the subagent succeed or fail?
"""
import json
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

    if not ACTIVE_SESSION_FILE.exists():
        sys.exit(0)
    try:
        session_id = json.loads(ACTIVE_SESSION_FILE.read_text()).get("session_id", "")
    except Exception:
        sys.exit(0)

    if not session_id:
        sys.exit(0)

    subagent_id = data.get("subagent_id", data.get("id", "unknown"))
    result = data.get("result", data.get("output", ""))
    # Failures are high importance
    failed = data.get("error") or data.get("failed") or False
    importance = 8 if failed else 5

    output_tail = scrub(
        f"SUBAGENT_STOP id:{subagent_id} failed:{failed}\nResult: {str(result)[-2000:]}"
    )

    obs = RawObservation(
        id=ids.observation_id(),
        session_id=session_id,
        timestamp=now(),
        tool="subagent_stop",
        tool_input_hash=subagent_id[:16] if subagent_id else "",
        output_tail=output_tail,
        importance_hint=importance,
    )

    try:
        storage = Storage()
        storage.append_observation(obs)
    except Exception as e:
        print(f"[moma] subagent_stop: ERROR: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
