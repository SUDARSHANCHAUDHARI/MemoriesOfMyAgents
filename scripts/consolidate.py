#!/usr/bin/env python3
"""
Memory consolidation — finds near-duplicate or contradictory memories
and merges them via a single LLM call. Run manually or via MCP tool.

Usage: python3 scripts/consolidate.py [project_slug]
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, Memory, ids
from moma.storage import slugify
from moma.privacy import scrub
from moma.config import load as load_config

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

CONSOLIDATE_PROMPT = """You are a memory consolidation engine.
Given a list of memories from an AI coding agent, identify groups that are:
- Near-duplicates (same fact stated differently)
- Complementary (can be merged into a richer single memory)
- Contradictory (older one should be superseded)

For each group, produce ONE merged memory.
Do not merge memories that are genuinely different.

Output XML only:

<consolidations>
  <group>
    <merge_ids>id1,id2,id3</merge_ids>
    <type>architecture|preference|bug|workflow|fact|pattern</type>
    <scope>project|global</scope>
    <title>Merged title (max 80 chars)</title>
    <content>Merged content. Include WHY. 2-4 sentences.</content>
    <concepts>comma,separated</concepts>
    <importance>1-10</importance>
  </group>
</consolidations>

If nothing should be merged, output: <consolidations></consolidations>
"""


def call_claude(prompt: str, model: str) -> str:
    import urllib.request
    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "system": CONSOLIDATE_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read())
                return body["content"][0]["text"]
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


def parse_groups_xml(xml: str) -> list[dict]:
    import re
    groups = []
    for block in re.findall(r"<group>(.*?)</group>", xml, re.DOTALL):
        def tag(name):
            m = re.search(rf"<{name}>(.*?)</{name}>", block, re.DOTALL)
            return m.group(1).strip() if m else ""
        groups.append({
            "merge_ids": [i.strip() for i in tag("merge_ids").split(",") if i.strip()],
            "type": tag("type") or "fact",
            "scope": tag("scope") or "project",
            "title": tag("title"),
            "content": tag("content"),
            "concepts": [c.strip() for c in tag("concepts").split(",") if c.strip()],
            "importance": max(1, min(10, int(tag("importance") or "5"))),
        })
    return [g for g in groups if g["title"] and g["merge_ids"]]


def consolidate(project_slug: str = "", dry_run: bool = False) -> dict:
    storage = Storage()
    config = load_config()
    model = config["compression"]["model"]

    mems = storage.list_memories(project_slug=project_slug if project_slug else None)
    active = [m for m in mems if not m.get("superseded_by")]

    if len(active) < 3:
        return {"skipped": "fewer than 3 active memories — nothing to consolidate"}

    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set"}

    mem_text = "\n".join(
        f"[id:{m['id']}] [{m['type']}] importance:{m['importance']} | {m['title']}: {m['content'][:200]}"
        for m in active[:60]
    )
    prompt = f"Project: {project_slug or 'all'}\n\nMemories:\n{mem_text}"

    try:
        response = call_claude(prompt, model)
    except Exception as e:
        return {"error": str(e)}

    groups = parse_groups_xml(response)
    if not groups:
        return {"merged": 0, "message": "no consolidation needed"}

    now = datetime.now(timezone.utc).isoformat()
    merged_count = 0

    for group in groups:
        if dry_run:
            print(f"Would merge {group['merge_ids']} → '{group['title']}'")
            continue

        # Find source memories
        source_mems = [m for m in active if m["id"] in group["merge_ids"]]
        if len(source_mems) < 2:
            continue

        # Gather all session_ids and files
        all_sessions = list({sid for m in source_mems for sid in m.get("session_ids", [])})
        all_files = list({f for m in source_mems for f in m.get("files", [])})
        all_source_obs = list({o for m in source_mems for o in m.get("source_observation_ids", [])})

        content = scrub(group["content"])
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if storage.is_duplicate(content_hash):
            continue

        scope = group["scope"] if group["scope"] in ("project", "global") else "project"
        mem_project = "global" if scope == "global" else (project_slug or "unknown")
        valid_types = {"pattern", "preference", "architecture", "bug", "workflow", "fact", "procedural"}
        mem_type = group["type"] if group["type"] in valid_types else "fact"

        merged = Memory(
            id=ids.memory_id(),
            type=mem_type,
            scope=scope,
            project=mem_project,
            title=group["title"],
            content=content,
            concepts=group["concepts"],
            files=all_files,
            importance=group["importance"],
            confidence=0.90,
            created_at=now,
            updated_at=now,
            session_ids=all_sessions,
            supersedes=group["merge_ids"],
            source_observation_ids=all_source_obs,
        )

        storage.save_memory(merged)
        storage.record_audit("memory_consolidated", merged.id, f"merged: {group['merge_ids']}")
        merged_count += 1

        # Mark source memories as superseded
        for m in source_mems:
            for path in storage.root.rglob(f"{m['id']}.md"):
                import re
                text = path.read_text()
                text = re.sub(r'^superseded_by: .*', f'superseded_by: "{merged.id}"', text, flags=re.MULTILINE)
                storage._atomic_write(path, text)

    return {"merged": merged_count, "groups": len(groups)}


if __name__ == "__main__":
    project = sys.argv[1] if len(sys.argv) > 1 else ""
    dry = "--dry-run" in sys.argv
    result = consolidate(project, dry_run=dry)
    print(json.dumps(result, indent=2))
