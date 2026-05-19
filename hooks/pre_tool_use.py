#!/usr/bin/env python3
"""
PreToolUse hook — evaluates GuardLocks.
block  → exit 2 (Claude Code treats non-zero as block)
warn   → print warning to stdout, exit 0
confirm → not yet implemented, treated as warn
"""
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma.config import load as load_config


def check_guardlocks(tool_name: str, tool_input: dict, cwd: str, git_branch: str) -> tuple[str, str]:
    """Returns (decision, message). decision: allow|warn|block"""
    config = load_config()
    guardlocks = config.get("guardlocks", [])

    for rule in guardlocks:
        if not rule.get("enabled", True):
            continue

        pattern = rule.get("pattern", {})
        matched = False

        # Tool match
        if "tool" in pattern:
            tool_regex = pattern["tool"]
            if re.search(tool_regex, tool_name):
                matched = True

        # Branch match
        if "branch" in pattern:
            branch_regex = pattern["branch"]
            if re.search(branch_regex, git_branch):
                matched = True

        # Content match (searches tool input)
        if "contains" in pattern:
            input_str = json.dumps(tool_input)
            if pattern["contains"].lower() in input_str.lower():
                matched = True

        # Regex match against input
        if "regex" in pattern:
            input_str = json.dumps(tool_input)
            if re.search(pattern["regex"], input_str, re.IGNORECASE):
                matched = True

        if matched:
            return rule.get("action", "warn"), rule.get("message", "GuardLock triggered.")

    return "allow", ""


def main():
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        print(f"[moma] pre_tool_use: failed to parse input: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd", "")
    git_branch = data.get("git_branch", "")

    decision, message = check_guardlocks(tool_name, tool_input, cwd, git_branch)

    if decision == "block":
        print(f"[moma GuardLock] BLOCKED: {message}", file=sys.stderr)
        sys.exit(2)
    elif decision in ("warn", "confirm"):
        print(f"[moma GuardLock] WARNING: {message}", file=sys.stderr)
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
