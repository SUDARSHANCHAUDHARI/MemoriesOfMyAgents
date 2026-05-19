#!/usr/bin/env python3
"""
Export/Import memories — portable JSON bundle.

Export: python3 scripts/export_import.py export [project_slug] > memories.json
Import: python3 scripts/export_import.py import memories.json [--project slug]
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, Memory, ids
from moma.storage import slugify


def export_memories(project_slug: str = "", scope: str = "all") -> dict:
    storage = Storage()
    mems = storage.list_memories(project_slug=project_slug if project_slug else None)
    active = [m for m in mems if not m.get("superseded_by")]
    if scope == "global":
        active = [m for m in active if m.get("scope") == "global"]
    elif scope == "project" and project_slug:
        active = [m for m in active if m.get("project") == project_slug]
    return {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": project_slug,
        "count": len(active),
        "memories": active,
    }


def import_memories(bundle: dict, target_project: str = "") -> dict:
    storage = Storage()
    now = datetime.now(timezone.utc).isoformat()
    imported = 0
    skipped = 0

    for m_data in bundle.get("memories", []):
        content = m_data.get("content", "")
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if storage.is_duplicate(content_hash):
            skipped += 1
            continue

        project = target_project or m_data.get("project", "unknown")
        scope = m_data.get("scope", "project")
        valid_types = {"pattern", "preference", "architecture", "bug", "workflow", "fact", "procedural", "conflict"}
        mem_type = m_data.get("type", "fact")
        if mem_type not in valid_types:
            mem_type = "fact"

        memory = Memory(
            id=ids.memory_id(),
            type=mem_type,
            scope=scope,
            project="global" if scope == "global" else project,
            title=m_data.get("title", "imported memory"),
            content=content,
            concepts=m_data.get("concepts", []),
            files=m_data.get("files", []),
            importance=m_data.get("importance", 5),
            confidence=m_data.get("confidence", 0.8),
            created_at=m_data.get("created_at", now),
            updated_at=now,
            session_ids=["import"],
        )
        storage.save_memory(memory)
        storage.record_audit("memory_imported", memory.id, f"from bundle: {bundle.get('project','?')}")
        imported += 1

    return {"imported": imported, "skipped": skipped}


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "export"
    if action == "export":
        project = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(export_memories(project), indent=2))
    elif action == "import":
        if len(sys.argv) < 3:
            print("Usage: export_import.py import <file.json> [project_slug]")
            sys.exit(1)
        bundle_path = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else ""
        with open(bundle_path) as f:
            bundle = json.load(f)
        print(json.dumps(import_memories(bundle, target), indent=2))
