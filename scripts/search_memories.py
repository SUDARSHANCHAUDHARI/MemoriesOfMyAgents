#!/usr/bin/env python3
"""
Search and rank memories for context injection.

Retrieval pipeline (3 signals fused with RRF):
  1. BM25       — keyword relevance (no ML deps)
  2. Recency    — Ebbinghaus decay (high-importance memories decay slower)
  3. File overlap — direct file path match boost

Used by prompt_submit hook and MCP server.
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma import Storage
from moma.bm25 import BM25
from moma.vectors import vector_rank
from moma.config import load as load_config


# ── Ebbinghaus decay ─────────────────────────────────────────────────────────
# retention(t) = exp(-t / stability)
# stability = importance * 5  →  high-importance memories fade slower
# importance=10 → 50-day half-life, importance=1 → 5-day half-life

def ebbinghaus_score(mem: dict, now_ts: float) -> float:
    try:
        updated = datetime.fromisoformat(mem.get("updated_at", "").replace("Z", "+00:00"))
        age_days = (now_ts - updated.timestamp()) / 86400
    except Exception:
        return 0.5
    importance = mem.get("importance", 5)
    stability = importance * 5.0  # days
    return math.exp(-age_days / stability)


# ── File overlap score ────────────────────────────────────────────────────────

def file_overlap_score(mem: dict, project_files: list[str]) -> float:
    mem_files = set(mem.get("files", []))
    proj_files = set(project_files)
    if not mem_files or not proj_files:
        return 0.0
    return min(1.0, len(mem_files & proj_files) / max(len(mem_files), 1))


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────
# Fuses ranked lists without needing score normalization.
# k=60 is standard RRF constant.

def rrf_fuse(ranked_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return scores


# ── Main retrieval ────────────────────────────────────────────────────────────

def get_relevant_memories(
    query: str,
    project_slug: str,
    project_files: list[str],
    max_tokens: int = 2000,
) -> list[dict]:
    storage = Storage()
    config = load_config()
    weights = config["injection"]["weights"]
    now_ts = datetime.now(timezone.utc).timestamp()

    # Gather all candidate memories
    project_mems = storage.list_memories(project_slug=project_slug)
    global_mems = storage.list_memories(scope="global")
    all_mems_map = {m["id"]: m for m in project_mems + global_mems}
    all_mems = [m for m in all_mems_map.values() if not m.get("superseded_by")]

    if not all_mems:
        return []

    # Build documents for BM25
    docs = [
        f"{m['title']} {m['content']} {' '.join(m.get('concepts', []))}"
        for m in all_mems
    ]
    bm25 = BM25(docs)

    # ── Signal 1: BM25 ranked list ──
    bm25_ranked = [idx for idx, _ in bm25.rank(query) if _ > 0]
    # All docs with score=0 go to end
    zero_score = [i for i in range(len(all_mems)) if i not in bm25_ranked]
    bm25_ranked_full = bm25_ranked + zero_score

    # ── Signal 2: Ebbinghaus recency ranked list ──
    recency_scores = [(i, ebbinghaus_score(m, now_ts)) for i, m in enumerate(all_mems)]
    recency_ranked = [i for i, _ in sorted(recency_scores, key=lambda x: x[1], reverse=True)]

    # ── Signal 3: File overlap ranked list ──
    file_scores = [(i, file_overlap_score(m, project_files)) for i, m in enumerate(all_mems)]
    file_ranked = [i for i, _ in sorted(file_scores, key=lambda x: x[1], reverse=True)]

    # ── Signal 4: TF-IDF / Vector similarity ──
    vector_scores = vector_rank(query, docs)
    vector_ranked = [idx for idx, _ in vector_scores]

    # ── Fuse with RRF (4 signals) ──
    fused = rrf_fuse([bm25_ranked_full, recency_ranked, file_ranked, vector_ranked])

    # Apply importance weighting on top of RRF
    final_scores = {
        idx: fused[idx] + all_mems[idx].get("importance", 5) / 10.0 * 0.2
        for idx in range(len(all_mems))
    }

    ranked_mems = sorted(
        [(score, all_mems[idx]) for idx, score in final_scores.items()],
        key=lambda x: x[0],
        reverse=True,
    )

    # Pack within token budget (~4 chars per token)
    result = []
    used_chars = 0
    budget_chars = max_tokens * 4

    for _, mem in ranked_mems:
        chunk = f"{mem['title']}: {mem['content']}"
        if used_chars + len(chunk) > budget_chars:
            break
        result.append(mem)
        used_chars += len(chunk)

    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def format_context(memories: list[dict], project: str) -> str:
    if not memories:
        return ""

    by_type: dict[str, list] = {}
    for mem in memories:
        t = mem.get("type", "fact").upper()
        by_type.setdefault(t, []).append(mem)

    lines = [f'<moma-context project="{project}">']
    for type_name, mems in sorted(by_type.items()):
        lines.append(f"\n{type_name}")
        for m in mems:
            cite = ""
            if m.get("source_observation_ids"):
                cite = f" [src:{m['source_observation_ids'][0][:8]}]"
            lines.append(f"- {m['title']}: {m['content']}{cite}")
    lines.append("\n</moma-context>")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--project", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = get_relevant_memories(args.query, args.project, [])
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_context(results, args.project))
