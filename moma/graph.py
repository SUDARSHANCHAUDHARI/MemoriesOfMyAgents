"""
Knowledge graph — entities and relationships extracted from memories.
Stored at ~/.moma/graph/graph.json
Format: {nodes: [{id, label, type, project, importance}], edges: [{from, to, relation, weight}]}
"""
import json
import re
from pathlib import Path
from typing import Optional

from .config import MOMA_ROOT

GRAPH_PATH = MOMA_ROOT / "graph" / "graph.json"


def _load() -> dict:
    if GRAPH_PATH.exists():
        try:
            return json.loads(GRAPH_PATH.read_text())
        except Exception:
            pass
    return {"nodes": [], "edges": []}


def _save(graph: dict) -> None:
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = GRAPH_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(graph, indent=2))
    tmp.replace(GRAPH_PATH)


def add_memory_to_graph(memory_id: str, title: str, content: str, concepts: list[str],
                         project: str, importance: int, mem_type: str) -> None:
    """Add a memory as a node; link to concept nodes via edges."""
    graph = _load()
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges_set = {(e["from"], e["to"], e["relation"]) for e in graph["edges"]}

    # Memory node
    mem_node_id = f"mem:{memory_id}"
    nodes[mem_node_id] = {
        "id": mem_node_id,
        "label": title[:60],
        "type": mem_type,
        "project": project,
        "importance": importance,
        "node_kind": "memory",
    }

    # Concept nodes + edges
    for concept in concepts[:8]:
        concept = concept.strip().lower()
        if not concept:
            continue
        concept_id = f"concept:{concept}"
        if concept_id not in nodes:
            nodes[concept_id] = {
                "id": concept_id,
                "label": concept,
                "type": "concept",
                "project": project,
                "importance": 3,
                "node_kind": "concept",
            }
        edge_key = (mem_node_id, concept_id, "relates_to")
        if edge_key not in edges_set:
            graph["edges"].append({"from": mem_node_id, "to": concept_id, "relation": "relates_to", "weight": 1})
            edges_set.add(edge_key)

    # Co-concept edges (concepts that appear together strengthen relationship)
    concept_ids = [f"concept:{c.strip().lower()}" for c in concepts if c.strip()]
    for i in range(len(concept_ids)):
        for j in range(i + 1, min(len(concept_ids), 5)):
            edge_key = (concept_ids[i], concept_ids[j], "co_occurs")
            if edge_key not in edges_set:
                graph["edges"].append({"from": concept_ids[i], "to": concept_ids[j], "relation": "co_occurs", "weight": 1})
                edges_set.add(edge_key)
            else:
                # Strengthen existing edge
                for e in graph["edges"]:
                    if e["from"] == concept_ids[i] and e["to"] == concept_ids[j] and e["relation"] == "co_occurs":
                        e["weight"] = e.get("weight", 1) + 1

    graph["nodes"] = list(nodes.values())
    _save(graph)


def get_graph() -> dict:
    return _load()


def get_graph_stats() -> dict:
    graph = _load()
    node_types: dict[str, int] = {}
    for n in graph["nodes"]:
        t = n.get("node_kind", "unknown")
        node_types[t] = node_types.get(t, 0) + 1
    return {
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "node_types": node_types,
    }


def get_related_memories(concept: str, limit: int = 10) -> list[str]:
    """Return memory node IDs related to a concept."""
    graph = _load()
    concept_id = f"concept:{concept.strip().lower()}"
    related = []
    for e in graph["edges"]:
        if e["to"] == concept_id and e["from"].startswith("mem:"):
            related.append(e["from"].replace("mem:", ""))
        elif e["from"] == concept_id and e["to"].startswith("mem:"):
            related.append(e["to"].replace("mem:", ""))
    return related[:limit]
