#!/usr/bin/env python3
"""
PreCompact hook — fires before Claude Code compacts the conversation.
Saves a snapshot of current context so memories survive compaction.
Also bumps access_count on any memories injected this session.
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
        session_info = json.loads(ACTIVE_SESSION_FILE.read_text())
        session_id = session_info.get("session_id", "")
    except Exception:
        sys.exit(0)

    if not session_id:
        sys.exit(0)

    storage = Storage()

    # Record the pre-compact event as an observation
    context = data.get("summary", data.get("context", ""))
    output_tail = scrub(f"PRE_COMPACT: conversation being compressed\n{str(context)[:500]}")

    obs = RawObservation(
        id=ids.observation_id(),
        session_id=session_id,
        timestamp=now(),
        tool="pre_compact",
        tool_input_hash="",
        output_tail=output_tail,
        importance_hint=6,
    )

    try:
        storage.append_observation(obs)
    except Exception as e:
        print(f"[moma] pre_compact: ERROR: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
