#!/usr/bin/env python3
"""
PostToolUse hook — appends raw observation to JSONL.
No LLM call. Pure file append. Errors go to stderr only.
output_tail = LAST 4000 chars (errors live at the end, not the start).
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, RawObservation, ids

OUTPUT_TAIL_CHARS = 4000

IMPORTANCE_HINTS = {
    "Write": 7,
    "Edit": 7,
    "Bash": 5,
    "Read": 2,
    "Glob": 1,
    "Grep": 2,
    "WebFetch": 4,
    "WebSearch": 3,
    "Agent": 6,
    "TodoWrite": 4,
}

SKIP_TOOLS = {"mcp__ccd_session__mark_chapter"}


def tail(text: str, n: int) -> str:
    if isinstance(text, str):
        return text[-n:] if len(text) > n else text
    try:
        s = json.dumps(text)
        return s[-n:] if len(s) > n else s
    except Exception:
        return str(text)[-n:]


def input_hash(tool_input) -> str:
    try:
        raw = json.dumps(tool_input, sort_keys=True) if not isinstance(tool_input, str) else tool_input
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[moma] post_tool_use: failed to parse input: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name = data.get("tool_name", "unknown")

    if tool_name in SKIP_TOOLS:
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    tool_input = data.get("tool_input", {})
    tool_output = data.get("tool_output", "")

    obs = RawObservation(
        id=ids.observation_id(),
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        tool=tool_name,
        tool_input_hash=input_hash(tool_input),
        output_tail=tail(tool_output, OUTPUT_TAIL_CHARS),
        importance_hint=IMPORTANCE_HINTS.get(tool_name, 3),
    )

    try:
        storage = Storage()
        storage.append_observation(obs)
    except Exception as e:
        print(f"[moma] post_tool_use: failed to append observation: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
