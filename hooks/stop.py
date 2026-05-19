#!/usr/bin/env python3
"""
Stop hook — triggers async compression pipeline.
Non-blocking: fires subprocess and exits immediately.
Agent is never held waiting for compression.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[moma] stop: failed to parse input: {e}", file=sys.stderr)
        sys.exit(0)

    session_id = data.get("session_id", "")
    if not session_id:
        sys.exit(0)

    compress_script = PROJECT_DIR / "scripts" / "compress_session.py"
    if not compress_script.exists():
        sys.exit(0)

    try:
        subprocess.Popen(
            [sys.executable, str(compress_script), session_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        print(f"[moma] stop: failed to launch compression: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
