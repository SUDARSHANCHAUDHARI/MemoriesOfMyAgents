import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import MOMA_ROOT
from .types import Memory, Session, RawObservation


class Storage:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or MOMA_ROOT

    # ── init ──────────────────────────────────────────────────────────────

    def init(self) -> None:
        dirs = [
            self.root / "sessions",
            self.root / "raw",
            self.root / "compressed",
            self.root / "memories" / "global",
            self.root / "index",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        index = self.root / "index" / "MEMORY_INDEX.md"
        if not index.exists():
            index.write_text("# MemoriesOfMyAgents — Memory Index\n\n")

        dedup = self.root / "index" / "dedup.json"
        if not dedup.exists():
            self._write_json(dedup, {})

        conflicts = self.root / "index" / "conflicts.json"
        if not conflicts.exists():
            self._write_json(conflicts, [])

        audit = self.root / "index" / "audit.json"
        if not audit.exists():
            self._write_json(audit, [])

    # ── sessions ──────────────────────────────────────────────────────────

    def save_session(self, session: Session) -> None:
        path = self.root / "sessions" / f"{session.id}.json"
        data = {
            "id": session.id,
            "project": session.project,
            "project_slug": session.project_slug,
            "cwd": session.cwd,
            "agent": session.agent,
            "git_branch": session.git_branch,
            "model": session.model,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "intent": {
                "raw": session.intent.raw,
                "task_type": session.intent.task_type,
                "domain": session.intent.domain,
                "files_mentioned": session.intent.files_mentioned,
                "goal": session.intent.goal,
            } if session.intent else None,
        }
        self._atomic_write(path, json.dumps(data, indent=2))

    def load_session(self, session_id: str) -> Optional[dict]:
        path = self.root / "sessions" / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def end_session(self, session_id: str) -> None:
        session = self.load_session(session_id)
        if session:
            session["ended_at"] = _now()
            path = self.root / "sessions" / f"{session_id}.json"
            self._atomic_write(path, json.dumps(session, indent=2))

    def list_sessions(self) -> list[dict]:
        sessions = []
        for p in sorted((self.root / "sessions").glob("*.json")):
            with open(p) as f:
                sessions.append(json.load(f))
        return sessions

    # ── raw observations ──────────────────────────────────────────────────

    def append_observation(self, obs: RawObservation) -> None:
        path = self.root / "raw" / f"{obs.session_id}.jsonl"
        line = json.dumps({
            "id": obs.id,
            "session_id": obs.session_id,
            "timestamp": obs.timestamp,
            "tool": obs.tool,
            "tool_input_hash": obs.tool_input_hash,
            "output_tail": obs.output_tail,
            "importance_hint": obs.importance_hint,
        })
        with open(path, "a") as f:
            f.write(line + "\n")

    def load_observations(self, session_id: str) -> list[dict]:
        path = self.root / "raw" / f"{session_id}.jsonl"
        if not path.exists():
            return []
        obs = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    obs.append(json.loads(line))
        return obs

    # ── memories ─────────────────────────────────────────────────────────

    def save_memory(self, memory: Memory) -> None:
        if memory.scope == "global":
            dir_path = self.root / "memories" / "global" / memory.type
        else:
            dir_path = self.root / "memories" / memory.project / memory.type
        dir_path.mkdir(parents=True, exist_ok=True)

        content = _memory_to_markdown(memory)
        path = dir_path / f"{memory.id}.md"
        self._atomic_write(path, content)
        self._update_dedup(memory)
        self._update_index(memory)

    def load_memory(self, memory_id: str) -> Optional[dict]:
        for path in self.root.rglob(f"{memory_id}.md"):
            return _parse_memory_markdown(path.read_text())
        return None

    def list_memories(self, project_slug: Optional[str] = None, scope: Optional[str] = None) -> list[dict]:
        memories = []
        search_root = self.root / "memories"
        for path in sorted(search_root.rglob("*.md")):
            parsed = _parse_memory_markdown(path.read_text())
            if not parsed:
                continue
            if scope and parsed.get("scope") != scope:
                continue
            if project_slug and parsed.get("project") != project_slug and parsed.get("scope") != "global":
                continue
            memories.append(parsed)
        return memories

    def search_memories(self, query: str, project_slug: Optional[str] = None) -> list[dict]:
        keywords = query.lower().split()
        results = []
        for mem in self.list_memories(project_slug=project_slug):
            text = f"{mem.get('title','')} {mem.get('content','')} {' '.join(mem.get('concepts',[]))}".lower()
            if any(kw in text for kw in keywords):
                results.append(mem)
        return results

    # ── dedup ─────────────────────────────────────────────────────────────

    def is_duplicate(self, content_hash: str) -> bool:
        dedup = self._load_dedup()
        return content_hash in dedup

    def _update_dedup(self, memory: Memory) -> None:
        import hashlib
        h = hashlib.sha256(memory.content.encode()).hexdigest()
        dedup = self._load_dedup()
        dedup[h] = {"memory_id": memory.id, "added_at": memory.created_at}
        self._write_json(self.root / "index" / "dedup.json", dedup)

    def _load_dedup(self) -> dict:
        path = self.root / "index" / "dedup.json"
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    # ── conflicts ────────────────────────────────────────────────────────

    def record_conflict(self, old_memory_id: str, new_memory_id: str, reason: str) -> None:
        path = self.root / "index" / "conflicts.json"
        conflicts = []
        if path.exists():
            with open(path) as f:
                conflicts = json.load(f)
        conflicts.append({
            "old_memory_id": old_memory_id,
            "new_memory_id": new_memory_id,
            "reason": reason,
            "detected_at": _now(),
        })
        self._write_json(path, conflicts)

    # ── access tracking (Ebbinghaus reinforcement) ────────────────────────

    def bump_access_count(self, memory_id: str) -> None:
        """Increment access_count — recalled memories strengthen in importance."""
        for path in self.root.rglob(f"{memory_id}.md"):
            text = path.read_text()
            parsed = _parse_memory_markdown(text)
            if not parsed:
                return
            new_count = parsed.get("access_count", 0) + 1
            text = re.sub(r"^access_count: \d+", f"access_count: {new_count}", text, flags=re.MULTILINE)
            self._atomic_write(path, text)
            return

    # ── audit log ─────────────────────────────────────────────────────────

    def record_audit(self, action: str, memory_id: str, detail: str = "") -> None:
        path = self.root / "index" / "audit.json"
        log = []
        if path.exists():
            with open(path) as f:
                log = json.load(f)
        log.append({"action": action, "memory_id": memory_id, "detail": detail, "at": _now()})
        self._write_json(path, log[-500:])  # keep last 500 entries

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        path = self.root / "index" / "audit.json"
        if not path.exists():
            return []
        with open(path) as f:
            log = json.load(f)
        return log[-limit:]

    # ── compressed sessions ───────────────────────────────────────────────

    def save_compressed(self, session_id: str, data: dict) -> None:
        path = self.root / "compressed" / f"{session_id}.json"
        self._atomic_write(path, json.dumps(data, indent=2))

    def load_compressed(self, session_id: str) -> Optional[dict]:
        path = self.root / "compressed" / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    # ── helpers ───────────────────────────────────────────────────────────

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(path, json.dumps(data, indent=2))

    def _update_index(self, memory: Memory) -> None:
        index_path = self.root / "index" / "MEMORY_INDEX.md"
        line = f"- [{memory.title}](../memories/{memory.project}/{memory.type}/{memory.id}.md) — {memory.type} | importance:{memory.importance}\n"
        with open(index_path, "a") as f:
            f.write(line)


# ── markdown serialization ────────────────────────────────────────────────

def _memory_to_markdown(m: Memory) -> str:
    return f"""---
id: {m.id}
type: {m.type}
scope: {m.scope}
project: {m.project}
importance: {m.importance}
confidence: {m.confidence}
created_at: {m.created_at}
updated_at: {m.updated_at}
session_ids: {json.dumps(m.session_ids)}
concepts: {json.dumps(m.concepts)}
files: {json.dumps(m.files)}
supersedes: {json.dumps(m.supersedes)}
superseded_by: {json.dumps(m.superseded_by)}
source_observation_ids: {json.dumps(m.source_observation_ids)}
access_count: {m.access_count}
---

{m.title}

{m.content}
"""


def _parse_memory_markdown(text: str) -> Optional[dict]:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1].strip()
    body = parts[2].strip()

    data = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip()

    lines = body.splitlines()
    title = lines[0].strip() if lines else ""
    content = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""

    return {
        "id": data.get("id", ""),
        "type": data.get("type", "fact"),
        "scope": data.get("scope", "project"),
        "project": data.get("project", ""),
        "importance": int(data.get("importance", 5)),
        "confidence": float(data.get("confidence", 0.8)),
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "session_ids": _parse_json_field(data.get("session_ids", "[]")),
        "concepts": _parse_json_field(data.get("concepts", "[]")),
        "files": _parse_json_field(data.get("files", "[]")),
        "supersedes": _parse_json_field(data.get("supersedes", "[]")),
        "superseded_by": _parse_json_field(data.get("superseded_by", "null")),
        "source_observation_ids": _parse_json_field(data.get("source_observation_ids", "[]")),
        "access_count": int(data.get("access_count", "0")),
        "title": title,
        "content": content,
    }


def _parse_json_field(val: str):
    try:
        return json.loads(val)
    except Exception:
        return val


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
