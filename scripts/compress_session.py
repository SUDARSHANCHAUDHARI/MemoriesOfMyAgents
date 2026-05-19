#!/usr/bin/env python3
"""
Compression pipeline — runs at session end (triggered by stop.py).
One LLM call per session. Full context. Not per tool call.

- Privacy filtering: secrets stripped before LLM sees observations
- Citation provenance: source_observation_ids tracked per memory
- Circuit breaker: retry with exponential backoff, API-key-less fallback
- 4-tier classification: working → episodic → semantic/procedural → conflict
- Ebbinghaus: access_count preserved across compression cycles
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage, Memory, ids
from moma.config import load as load_config
from moma.privacy import scrub
from moma.graph import add_memory_to_graph

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a memory extraction engine for an AI coding agent.
Your job: given a session's goal and all actions taken, extract memories worth keeping long-term.

Memory tiers — classify each memory:
- semantic:    factual knowledge (architecture decisions, config values, APIs)
- procedural:  how-to knowledge (workflows, repeatable steps, patterns)
- preference:  user preferences, style choices, feedback on your approach
- bug:         root causes and fixes (include the fix, not just "fixed")
- conflict:    contradictions with existing knowledge

Rules:
- Only extract if it would genuinely help future sessions.
- Prefer fewer, higher-quality memories (0-5 max).
- Include WHY in content, not just WHAT.
- scope=global means it applies to any project.
- scope=project means it's specific to this codebase.
- If a memory contradicts an existing one, set contradicts to the existing title exactly.
- NEVER include secrets, tokens, passwords, or API keys — these are already stripped.

Output ONLY valid XML. No extra text."""

EXTRACTION_PROMPT = """\
Session goal: {goal}
Project: {project}
Agent: {agent}
Duration: {duration}

Actions taken this session (in order, ids for citation):
{actions}

Existing memory titles (do not duplicate):
{existing_titles}

Extract 0-5 memories. For each memory include the observation IDs it was derived from.

<memories>
  <memory>
    <type>semantic|procedural|preference|bug|fact|architecture|workflow</type>
    <scope>project|global</scope>
    <title>Short title max 80 chars</title>
    <content>2-3 sentences. Include WHY not just WHAT.</content>
    <concepts>comma,separated,terms</concepts>
    <files>comma,separated/file/paths</files>
    <importance>1-10</importance>
    <contradicts>exact title of conflicting existing memory, or empty</contradicts>
    <source_obs>obs_id1,obs_id2</source_obs>
  </memory>
</memories>
"""


# ── XML parsing ───────────────────────────────────────────────────────────────

def parse_memories_xml(xml: str) -> list[dict]:
    memories = []
    blocks = re.findall(r"<memory>(.*?)</memory>", xml, re.DOTALL)
    for block in blocks:
        def tag(name: str) -> str:
            m = re.search(rf"<{name}>(.*?)</{name}>", block, re.DOTALL)
            return m.group(1).strip() if m else ""

        memories.append({
            "type": tag("type") or "fact",
            "scope": tag("scope") or "project",
            "title": tag("title"),
            "content": tag("content"),
            "concepts": [c.strip() for c in tag("concepts").split(",") if c.strip()],
            "files": [f.strip() for f in tag("files").split(",") if f.strip()],
            "importance": max(1, min(10, int(tag("importance") or "5"))),
            "contradicts": tag("contradicts"),
            "source_obs": [s.strip() for s in tag("source_obs").split(",") if s.strip()],
        })
    return [m for m in memories if m["title"] and m["content"]]


# ── Circuit breaker LLM call ─────────────────────────────────────────────────

def call_claude(system: str, prompt: str, model: str, retries: int = 3) -> str:
    import urllib.request

    payload = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    last_err = None
    for attempt in range(retries):
        try:
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
                return body["content"][0]["text"]
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"[moma] LLM call attempt {attempt+1} failed: {e} — retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)

    raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("[moma] compress_session: missing session_id", file=sys.stderr)
        sys.exit(1)

    session_id = sys.argv[1]
    config = load_config()
    storage = Storage()
    model = config["compression"]["model"]
    max_memories = config["compression"]["max_memories_per_session"]
    min_importance = config["compression"]["min_importance"]

    session = storage.load_session(session_id)
    if not session:
        print(f"[moma] compress_session: session {session_id} not found", file=sys.stderr)
        sys.exit(1)

    observations = storage.load_observations(session_id)
    if not observations:
        storage.end_session(session_id)
        sys.exit(0)

    # Privacy-scrub all observations before LLM sees them
    scrubbed_obs = []
    for obs in observations:
        scrubbed_obs.append({**obs, "output_tail": scrub(obs.get("output_tail", ""))})

    # Build actions summary with IDs for citation
    actions_lines = []
    for obs in scrubbed_obs:
        actions_lines.append(
            f"- [id:{obs['id']}] [{obs['tool']}] hint:{obs['importance_hint']} | {obs['output_tail'][:300]}"
        )
    actions_text = "\n".join(actions_lines[:100])

    intent = session.get("intent") or {}
    goal = intent.get("goal") or intent.get("raw") or "general coding session"
    project = session.get("project", "unknown")
    project_slug = session.get("project_slug", "unknown")
    agent = session.get("agent", "unknown")

    started = session.get("started_at", "")
    now_str = datetime.now(timezone.utc).isoformat()
    try:
        from datetime import datetime as dt
        start_dt = dt.fromisoformat(started.replace("Z", "+00:00"))
        end_dt = dt.fromisoformat(now_str.replace("Z", "+00:00"))
        duration = str(end_dt - start_dt).split(".")[0]
    except Exception:
        duration = "unknown"

    existing = storage.list_memories(project_slug=project_slug)
    existing_titles = "\n".join(f"- {m['title']}" for m in existing[:50]) or "(none yet)"

    prompt = EXTRACTION_PROMPT.format(
        goal=goal,
        project=project,
        agent=agent,
        duration=duration,
        actions=actions_text,
        existing_titles=existing_titles,
    )

    if not ANTHROPIC_API_KEY:
        print("[moma] compress_session: ANTHROPIC_API_KEY not set — skipping LLM compression", file=sys.stderr)
        storage.end_session(session_id)
        sys.exit(0)

    try:
        response = call_claude(SYSTEM_PROMPT, prompt, model)
    except Exception as e:
        print(f"[moma] compress_session: LLM call failed: {e}", file=sys.stderr)
        storage.end_session(session_id)
        sys.exit(0)

    candidates = parse_memories_xml(response)
    candidates = candidates[:max_memories]

    now = datetime.now(timezone.utc).isoformat()
    saved = []
    valid_types = {"pattern", "preference", "architecture", "bug", "workflow", "fact", "conflict", "procedural", "semantic"}

    for candidate in candidates:
        if candidate["importance"] < min_importance:
            continue

        content = scrub(candidate["content"])  # extra safety pass
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if storage.is_duplicate(content_hash):
            continue

        # Conflict detection + audit
        contradicts = candidate.get("contradicts", "").strip()
        if contradicts:
            old_matches = [m for m in existing if m["title"].lower() == contradicts.lower()]
            if old_matches:
                old = old_matches[0]
                storage.record_conflict(old["id"], "pending", f"New memory contradicts: {contradicts}")
                storage.record_audit("conflict_detected", old["id"], f"contradicted by new memory: {candidate['title']}")

        scope = candidate["scope"] if candidate["scope"] in ("project", "global") else "project"
        mem_project = "global" if scope == "global" else project_slug

        # Map semantic/procedural to valid storage types
        raw_type = candidate["type"]
        if raw_type == "semantic":
            raw_type = "fact"
        elif raw_type == "procedural":
            raw_type = "workflow"
        mem_type = raw_type if raw_type in valid_types else "fact"

        memory = Memory(
            id=ids.memory_id(),
            type=mem_type,
            scope=scope,
            project=mem_project,
            title=candidate["title"],
            content=content,
            concepts=candidate["concepts"],
            files=candidate["files"],
            importance=candidate["importance"],
            confidence=0.85,
            created_at=now,
            updated_at=now,
            session_ids=[session_id],
            source_observation_ids=candidate.get("source_obs", []),
        )

        try:
            storage.save_memory(memory)
            storage.record_audit("memory_saved", memory.id, f"session:{session_id} type:{mem_type}")
            add_memory_to_graph(
                memory_id=memory.id,
                title=memory.title,
                content=memory.content,
                concepts=memory.concepts,
                project=mem_project,
                importance=memory.importance,
                mem_type=mem_type,
            )
            saved.append(memory.title)
        except Exception as e:
            print(f"[moma] compress_session: failed to save memory: {e}", file=sys.stderr)

    storage.save_compressed(session_id, {
        "session_id": session_id,
        "project": project,
        "goal": goal,
        "duration": duration,
        "observation_count": len(observations),
        "memories_saved": saved,
        "compressed_at": now,
    })

    storage.end_session(session_id)
    print(f"[moma] compressed session {session_id}: {len(saved)} memories saved", file=sys.stderr)


if __name__ == "__main__":
    main()
