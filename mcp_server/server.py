#!/usr/bin/env python3
"""
MemoriesOfMyAgents — MCP Server  (39 tools + 6 resources + 3 prompts)
Exposes memory tools to Cursor, Windsurf, Gemini CLI, any MCP client.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, Prompt, PromptMessage, PromptArgument
import mcp.types as types

from moma import Storage, Memory, Session, ids
from moma.storage import slugify
from moma.config import load as load_config, MOMA_ROOT
from moma.privacy import scrub
from moma.graph import get_graph, get_graph_stats, get_related_memories
from moma.team import list_teams, create_team, save_team_memory, list_team_memories, get_team_config
from moma import leases as _leases
from moma import git_snapshots as _snaps

import importlib.util as _ilu
_search = PROJECT_DIR / "scripts" / "search_memories.py"
_spec = _ilu.spec_from_file_location("search_memories", str(_search))
_mod = _ilu.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_mod)  # type: ignore
get_relevant_memories = _mod.get_relevant_memories
format_context = _mod.format_context

app = Server("moma")
storage = Storage()


# ── Tool definitions ──────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ── Core memory ops ──
        Tool(
            name="moma_memory_save",
            description="Save a memory. Use for important decisions, architecture facts, bugs, preferences, workflows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["pattern","preference","architecture","bug","workflow","fact","procedural"]},
                    "scope": {"type": "string", "enum": ["project","global"]},
                    "project": {"type": "string"},
                    "title": {"type": "string", "description": "Short title max 80 chars"},
                    "content": {"type": "string", "description": "2-3 sentences. Include WHY not just WHAT."},
                    "concepts": {"type": "array", "items": {"type": "string"}},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["type", "title", "content"],
            },
        ),
        Tool(
            name="moma_memory_search",
            description="Search memories using BM25 + Ebbinghaus ranking. Returns best matches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="moma_context_build",
            description="Build full ranked context for a project. Call at session start. Returns <moma-context> block.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "prompt": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "max_tokens": {"type": "integer", "default": 2000},
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="moma_memory_forget",
            description="Soft-delete a memory (marks as superseded). Provide memory_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="moma_memory_update",
            description="Update an existing memory's content or importance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "content": {"type": "string"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 10},
                    "concepts": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["memory_id"],
            },
        ),
        # ── Session ops ──
        Tool(
            name="moma_session_start",
            description="Register a new agent session. Returns session_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "cwd": {"type": "string"},
                    "agent": {"type": "string"},
                    "git_branch": {"type": "string"},
                },
                "required": ["project", "cwd"],
            },
        ),
        Tool(
            name="moma_session_end",
            description="End a session and trigger async memory compression.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        Tool(
            name="moma_sessions_list",
            description="List recent sessions with project, agent, duration, memory count.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "filter by project slug"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        # ── Analytics ──
        Tool(
            name="moma_memory_patterns",
            description="Find recurring patterns and frequent concepts across all memories for a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "top_n": {"type": "integer", "default": 10},
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="moma_file_history",
            description="Return all memories that reference a specific file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "project": {"type": "string"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="moma_project_profile",
            description="Return a summary profile of a project: top memories, frequent concepts, active files, agent usage.",
            inputSchema={
                "type": "object",
                "properties": {"project": {"type": "string"}},
                "required": ["project"],
            },
        ),
        Tool(
            name="moma_stats",
            description="Return store-wide stats: total memories, sessions, projects, storage size.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── GuardLocks ──
        Tool(
            name="moma_guardlock_check",
            description="Check if an action is allowed by GuardLocks. Returns allow|warn|block.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "tool_input": {"type": "object"},
                    "git_branch": {"type": "string"},
                    "action": {"type": "string", "description": "human description of what you're about to do"},
                },
                "required": ["tool_name"],
            },
        ),
        Tool(
            name="moma_guardlock_list",
            description="List all configured GuardLock rules.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Audit & provenance ──
        Tool(
            name="moma_audit_log",
            description="View recent audit log: memory saves, conflicts, deletions.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 30}},
            },
        ),
        Tool(
            name="moma_memory_provenance",
            description="Show which observations a memory was derived from (citation trail).",
            inputSchema={
                "type": "object",
                "properties": {"memory_id": {"type": "string"}},
                "required": ["memory_id"],
            },
        ),
        # ── Snapshots ──
        Tool(
            name="moma_snapshot_create",
            description="Create a git-versioned snapshot of the entire memory store.",
            inputSchema={
                "type": "object",
                "properties": {"label": {"type": "string", "description": "snapshot label"}},
            },
        ),
        Tool(
            name="moma_snapshot_list",
            description="List all snapshots.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Compression ──
        Tool(
            name="moma_compress_now",
            description="Manually trigger compression for a session (requires ANTHROPIC_API_KEY).",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        # ── Conflicts ──
        Tool(
            name="moma_conflicts_list",
            description="List detected memory conflicts that need resolution.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
            },
        ),
        # ── Knowledge graph ──
        Tool(
            name="moma_graph_stats",
            description="Return knowledge graph statistics: node count, edge count, type distribution.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="moma_graph_related",
            description="Find memories related to a concept via the knowledge graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["concept"],
            },
        ),
        # ── Team memory ──
        Tool(
            name="moma_team_create",
            description="Create a team shared memory namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "members": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="moma_team_save",
            description="Save a memory to a team's shared namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "type": {"type": "string", "enum": ["pattern","preference","architecture","bug","workflow","fact"]},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 10},
                    "visibility": {"type": "string", "enum": ["shared","private"], "default": "shared"},
                },
                "required": ["team", "title", "content"],
            },
        ),
        Tool(
            name="moma_team_search",
            description="Search a team's shared memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "query": {"type": "string"},
                    "visibility": {"type": "string", "enum": ["shared","private","both"], "default": "shared"},
                },
                "required": ["team", "query"],
            },
        ),
        Tool(
            name="moma_teams_list",
            description="List all configured teams.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Consolidation ──
        Tool(
            name="moma_consolidate",
            description="LLM-powered merge of near-duplicate or contradictory memories. Reduces noise. Requires ANTHROPIC_API_KEY.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project slug to consolidate. Empty = all projects."},
                    "dry_run": {"type": "boolean", "default": False, "description": "Preview merges without applying."},
                },
            },
        ),
        # ── Claude bridge ──
        Tool(
            name="moma_bridge_pull",
            description="Pull bullet points from a project's MEMORY.md or CLAUDE.md into moma memories.",
            inputSchema={
                "type": "object",
                "properties": {"project_dir": {"type": "string", "description": "Absolute path to the project directory"}},
                "required": ["project_dir"],
            },
        ),
        Tool(
            name="moma_bridge_push",
            description="Push top moma memories for a project back into its MEMORY.md file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "project": {"type": "string", "description": "Override project slug"},
                },
                "required": ["project_dir"],
            },
        ),
        # ── Export / import ──
        Tool(
            name="moma_export",
            description="Export memories to a portable JSON bundle (stdout or returned as text).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "scope": {"type": "string", "enum": ["all", "global", "project"], "default": "all"},
                },
            },
        ),
        Tool(
            name="moma_import",
            description="Import memories from a JSON bundle file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_path": {"type": "string", "description": "Absolute path to bundle .json file"},
                    "target_project": {"type": "string"},
                },
                "required": ["bundle_path"],
            },
        ),
        # ── Multi-agent leases ──
        Tool(
            name="moma_lease_acquire",
            description="Acquire a file-based lease (mutual exclusion) for a resource. Returns ok=true if acquired.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "e.g. 'memory:mem_abc123'"},
                    "holder": {"type": "string", "description": "Identifier for the agent holding the lease"},
                    "ttl": {"type": "integer", "default": 30, "description": "Seconds before auto-expiry"},
                },
                "required": ["resource_id"],
            },
        ),
        Tool(
            name="moma_lease_release",
            description="Release a previously acquired lease.",
            inputSchema={
                "type": "object",
                "properties": {"resource_id": {"type": "string"}},
                "required": ["resource_id"],
            },
        ),
        Tool(
            name="moma_leases_list",
            description="List all currently active (non-expired) leases.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Git-versioned snapshots (via moma/git_snapshots.py) ──
        Tool(
            name="moma_git_snapshot_create",
            description="Create a git-versioned snapshot of the memory store inside ~/.moma/.",
            inputSchema={
                "type": "object",
                "properties": {"label": {"type": "string", "description": "Human label for this snapshot"}},
            },
        ),
        Tool(
            name="moma_git_snapshot_list",
            description="List git-versioned snapshots (git log inside ~/.moma/).",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
            },
        ),
        Tool(
            name="moma_git_rollback",
            description="Roll back the memory store to a previous snapshot by commit SHA.",
            inputSchema={
                "type": "object",
                "properties": {"sha": {"type": "string", "description": "Git commit SHA to roll back to"}},
                "required": ["sha"],
            },
        ),
        Tool(
            name="moma_git_diff",
            description="Show git diff --stat between two snapshots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sha1": {"type": "string"},
                    "sha2": {"type": "string", "default": "HEAD"},
                },
                "required": ["sha1"],
            },
        ),
        # ── Health ──
        Tool(
            name="moma_health",
            description="Storage integrity check: orphaned files, missing indexes, corrupt frontmatter, lock leaks.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


# ── MCP Resources ─────────────────────────────────────────────────────────────

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="moma://status",
            name="moma status",
            description="Overall memory store status and stats",
            mimeType="application/json",
        ),
        Resource(
            uri="moma://memories/latest",
            name="Latest memories",
            description="Most recently updated memories across all projects",
            mimeType="application/json",
        ),
        Resource(
            uri="moma://graph/stats",
            name="Knowledge graph stats",
            description="Node and edge counts in the knowledge graph",
            mimeType="application/json",
        ),
        Resource(
            uri="moma://conflicts",
            name="Unresolved conflicts",
            description="Memory conflicts that need human review",
            mimeType="application/json",
        ),
        Resource(
            uri="moma://audit/recent",
            name="Recent audit log",
            description="Last 20 audit events",
            mimeType="application/json",
        ),
        Resource(
            uri="moma://teams",
            name="Teams",
            description="All configured team namespaces",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "moma://status":
        all_mems = storage.list_memories()
        all_sessions = storage.list_sessions()
        projects = set(m.get("project") for m in all_mems if m.get("scope") != "global")
        size_bytes = sum(f.stat().st_size for f in MOMA_ROOT.rglob("*") if f.is_file())
        return json.dumps({
            "total_memories": len(all_mems),
            "total_sessions": len(all_sessions),
            "total_projects": len(projects),
            "global_memories": sum(1 for m in all_mems if m.get("scope") == "global"),
            "storage_kb": round(size_bytes / 1024, 1),
            "graph_stats": get_graph_stats(),
        }, indent=2)
    elif uri == "moma://memories/latest":
        mems = storage.list_memories()
        mems.sort(key=lambda m: m.get("updated_at", ""), reverse=True)
        return json.dumps(mems[:20], indent=2)
    elif uri == "moma://graph/stats":
        return json.dumps(get_graph_stats(), indent=2)
    elif uri == "moma://conflicts":
        path = MOMA_ROOT / "index" / "conflicts.json"
        if path.exists():
            return path.read_text()
        return "[]"
    elif uri == "moma://audit/recent":
        return json.dumps(storage.get_audit_log(limit=20), indent=2)
    elif uri == "moma://teams":
        return json.dumps(list_teams(), indent=2)
    return json.dumps({"error": f"unknown resource: {uri}"})


# ── Tool implementations ──────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    now = datetime.now(timezone.utc).isoformat()

    # ── moma_memory_save ──
    if name == "moma_memory_save":
        project_slug = slugify(arguments.get("project", "unknown"))
        scope = arguments.get("scope", "project")
        mem_project = "global" if scope == "global" else project_slug
        valid_types = {"pattern", "preference", "architecture", "bug", "workflow", "fact", "procedural"}
        mem_type = arguments.get("type", "fact")
        if mem_type not in valid_types:
            mem_type = "fact"
        memory = Memory(
            id=ids.memory_id(),
            type=mem_type,
            scope=scope,
            project=mem_project,
            title=arguments["title"],
            content=scrub(arguments["content"]),
            concepts=arguments.get("concepts", []),
            files=arguments.get("files", []),
            importance=arguments.get("importance", 7),
            confidence=0.9,
            created_at=now,
            updated_at=now,
            session_ids=["mcp-manual"],
        )
        storage.save_memory(memory)
        storage.record_audit("memory_saved", memory.id, "via MCP manual save")
        return [TextContent(type="text", text=json.dumps({"saved": True, "id": memory.id}))]

    # ── moma_memory_search ──
    elif name == "moma_memory_search":
        query = arguments["query"]
        project = arguments.get("project", "")
        limit = arguments.get("limit", 10)
        config = load_config()
        results = get_relevant_memories(
            query=query,
            project_slug=slugify(project) if project else "",
            project_files=[],
            max_tokens=config["injection"]["max_tokens"],
        )
        for m in results:
            storage.bump_access_count(m["id"])
        return [TextContent(type="text", text=json.dumps(results[:limit], indent=2))]

    # ── moma_context_build ──
    elif name == "moma_context_build":
        project = arguments["project"]
        project_slug = slugify(project)
        prompt = arguments.get("prompt", project)
        files = arguments.get("files", [])
        max_tokens = arguments.get("max_tokens", load_config()["injection"]["max_tokens"])
        memories = get_relevant_memories(query=prompt, project_slug=project_slug, project_files=files, max_tokens=max_tokens)
        for m in memories:
            storage.bump_access_count(m["id"])
        context = format_context(memories, project)
        return [TextContent(type="text", text=context or "(no relevant memories found)")]

    # ── moma_memory_forget ──
    elif name == "moma_memory_forget":
        memory_id = arguments["memory_id"]
        reason = arguments.get("reason", "manual forget")
        mem = storage.load_memory(memory_id)
        if not mem:
            return [TextContent(type="text", text=json.dumps({"error": "memory not found"}))]
        storage.record_conflict(memory_id, "deleted", reason)
        storage.record_audit("memory_deleted", memory_id, reason)
        return [TextContent(type="text", text=json.dumps({"forgotten": True, "id": memory_id}))]

    # ── moma_memory_update ──
    elif name == "moma_memory_update":
        memory_id = arguments["memory_id"]
        for path in storage.root.rglob(f"{memory_id}.md"):
            text = path.read_text()
            if arguments.get("content"):
                new_content = scrub(arguments["content"])
                lines = text.split("\n")
                # Replace body after frontmatter
                parts = text.split("---", 2)
                if len(parts) == 3:
                    title_line = parts[2].strip().split("\n")[0]
                    text = f"---{parts[1]}---\n\n{title_line}\n\n{new_content}\n"
            if arguments.get("importance"):
                import re
                text = re.sub(r"^importance: \d+", f"importance: {arguments['importance']}", text, flags=re.MULTILINE)
            if arguments.get("concepts"):
                import re
                text = re.sub(r"^concepts: .*", f"concepts: {json.dumps(arguments['concepts'])}", text, flags=re.MULTILINE)
            text = re.sub(r"^updated_at: .*", f"updated_at: {now}", text, flags=re.MULTILINE)
            storage._atomic_write(path, text)
            storage.record_audit("memory_updated", memory_id, "via MCP update")
            return [TextContent(type="text", text=json.dumps({"updated": True, "id": memory_id}))]
        return [TextContent(type="text", text=json.dumps({"error": "memory not found"}))]

    # ── moma_session_start ──
    elif name == "moma_session_start":
        project = arguments["project"]
        session = Session(
            id=ids.session_id(),
            project=project,
            project_slug=slugify(project),
            cwd=arguments["cwd"],
            agent=arguments.get("agent", "mcp-client"),
            git_branch=arguments.get("git_branch", ""),
            started_at=now,
        )
        storage.save_session(session)
        return [TextContent(type="text", text=json.dumps({"session_id": session.id}))]

    # ── moma_session_end ──
    elif name == "moma_session_end":
        session_id = arguments["session_id"]
        storage.end_session(session_id)
        compress_script = PROJECT_DIR / "scripts" / "compress_session.py"
        if compress_script.exists():
            subprocess.Popen(
                [sys.executable, str(compress_script), session_id],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return [TextContent(type="text", text=json.dumps({"ended": True, "session_id": session_id}))]

    # ── moma_sessions_list ──
    elif name == "moma_sessions_list":
        project_filter = arguments.get("project", "")
        limit = arguments.get("limit", 20)
        sessions = storage.list_sessions()
        if project_filter:
            slug = slugify(project_filter)
            sessions = [s for s in sessions if s.get("project_slug") == slug]
        sessions = sessions[-limit:]
        # Enrich with memory count
        result = []
        for s in sessions:
            obs_path = storage.root / "raw" / f"{s['id']}.jsonl"
            obs_count = 0
            if obs_path.exists():
                obs_count = sum(1 for _ in obs_path.open())
            result.append({**s, "observation_count": obs_count})
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_memory_patterns ──
    elif name == "moma_memory_patterns":
        project = arguments["project"]
        top_n = arguments.get("top_n", 10)
        mems = storage.list_memories(project_slug=slugify(project))
        concept_freq: dict[str, int] = {}
        type_freq: dict[str, int] = {}
        for m in mems:
            for c in m.get("concepts", []):
                concept_freq[c] = concept_freq.get(c, 0) + 1
            t = m.get("type", "fact")
            type_freq[t] = type_freq.get(t, 0) + 1
        top_concepts = sorted(concept_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [TextContent(type="text", text=json.dumps({
            "project": project,
            "total_memories": len(mems),
            "type_distribution": type_freq,
            "top_concepts": [{"concept": c, "count": n} for c, n in top_concepts],
        }, indent=2))]

    # ── moma_file_history ──
    elif name == "moma_file_history":
        file_path = arguments["file_path"]
        project = arguments.get("project", "")
        mems = storage.list_memories(project_slug=slugify(project) if project else None)
        matches = [m for m in mems if any(file_path in f for f in m.get("files", []))]
        return [TextContent(type="text", text=json.dumps(matches, indent=2))]

    # ── moma_project_profile ──
    elif name == "moma_project_profile":
        project = arguments["project"]
        slug = slugify(project)
        mems = storage.list_memories(project_slug=slug)
        sessions = [s for s in storage.list_sessions() if s.get("project_slug") == slug]
        agents = {}
        for s in sessions:
            a = s.get("agent", "unknown")
            agents[a] = agents.get(a, 0) + 1
        file_freq: dict[str, int] = {}
        for m in mems:
            for f in m.get("files", []):
                file_freq[f] = file_freq.get(f, 0) + 1
        top_mems = sorted(mems, key=lambda m: m.get("importance", 5), reverse=True)[:5]
        return [TextContent(type="text", text=json.dumps({
            "project": project,
            "total_memories": len(mems),
            "total_sessions": len(sessions),
            "agents_used": agents,
            "top_files": sorted(file_freq.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_memories": [{"title": m["title"], "importance": m["importance"], "type": m["type"]} for m in top_mems],
        }, indent=2))]

    # ── moma_stats ──
    elif name == "moma_stats":
        all_mems = storage.list_memories()
        all_sessions = storage.list_sessions()
        projects = set(m.get("project") for m in all_mems if m.get("scope") != "global")
        size_bytes = sum(f.stat().st_size for f in storage.root.rglob("*") if f.is_file())
        return [TextContent(type="text", text=json.dumps({
            "total_memories": len(all_mems),
            "total_sessions": len(all_sessions),
            "total_projects": len(projects),
            "global_memories": sum(1 for m in all_mems if m.get("scope") == "global"),
            "storage_kb": round(size_bytes / 1024, 1),
        }, indent=2))]

    # ── moma_guardlock_check ──
    elif name == "moma_guardlock_check":
        import re as _re
        config = load_config()
        tool_name = arguments["tool_name"]
        tool_input = arguments.get("tool_input", {})
        git_branch = arguments.get("git_branch", "")
        action = arguments.get("action", "")
        for rule in config.get("guardlocks", []):
            if not rule.get("enabled", True):
                continue
            pattern = rule.get("pattern", {})
            matched = False
            if "tool" in pattern and _re.search(pattern["tool"], tool_name):
                matched = True
            if "branch" in pattern and _re.search(pattern["branch"], git_branch):
                matched = True
            if "contains" in pattern and pattern["contains"].lower() in json.dumps(tool_input).lower():
                matched = True
            if "action" in pattern and action and _re.search(pattern["action"], action, _re.I):
                matched = True
            if matched:
                return [TextContent(type="text", text=json.dumps({
                    "decision": rule.get("action", "warn"),
                    "message": rule.get("message", "GuardLock triggered"),
                    "rule_id": rule.get("id", ""),
                }))]
        return [TextContent(type="text", text=json.dumps({"decision": "allow"}))]

    # ── moma_guardlock_list ──
    elif name == "moma_guardlock_list":
        config = load_config()
        return [TextContent(type="text", text=json.dumps(config.get("guardlocks", []), indent=2))]

    # ── moma_audit_log ──
    elif name == "moma_audit_log":
        limit = arguments.get("limit", 30)
        log = storage.get_audit_log(limit=limit)
        return [TextContent(type="text", text=json.dumps(log, indent=2))]

    # ── moma_memory_provenance ──
    elif name == "moma_memory_provenance":
        memory_id = arguments["memory_id"]
        mem = storage.load_memory(memory_id)
        if not mem:
            return [TextContent(type="text", text=json.dumps({"error": "memory not found"}))]
        source_ids = mem.get("source_observation_ids", [])
        session_ids = mem.get("session_ids", [])
        observations = []
        for sid in session_ids:
            for obs in storage.load_observations(sid):
                if obs["id"] in source_ids:
                    observations.append(obs)
        return [TextContent(type="text", text=json.dumps({
            "memory_id": memory_id,
            "title": mem.get("title"),
            "source_observation_ids": source_ids,
            "observations": observations,
        }, indent=2))]

    # ── moma_snapshot_create ──
    elif name == "moma_snapshot_create":
        label = arguments.get("label", "manual")
        snap_dir = storage.root / "snapshots"
        snap_dir.mkdir(exist_ok=True)
        snap_id = f"snap_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{label}"
        snap_path = snap_dir / f"{snap_id}.json"
        all_mems = storage.list_memories()
        snap_data = {"id": snap_id, "label": label, "created_at": now, "memory_count": len(all_mems), "memories": all_mems}
        storage._atomic_write(snap_path, json.dumps(snap_data, indent=2))
        storage.record_audit("snapshot_created", snap_id, label)
        return [TextContent(type="text", text=json.dumps({"snapshot_id": snap_id, "memories": len(all_mems)}))]

    # ── moma_snapshot_list ──
    elif name == "moma_snapshot_list":
        snap_dir = storage.root / "snapshots"
        snaps = []
        if snap_dir.exists():
            for f in sorted(snap_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text())
                    snaps.append({"id": data["id"], "label": data.get("label"), "created_at": data.get("created_at"), "memory_count": data.get("memory_count")})
                except Exception:
                    pass
        return [TextContent(type="text", text=json.dumps(snaps, indent=2))]

    # ── moma_compress_now ──
    elif name == "moma_compress_now":
        session_id = arguments["session_id"]
        compress_script = PROJECT_DIR / "scripts" / "compress_session.py"
        proc = subprocess.Popen(
            [sys.executable, str(compress_script), session_id],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=120)
        return [TextContent(type="text", text=json.dumps({
            "session_id": session_id,
            "exit_code": proc.returncode,
            "output": (stdout + stderr).decode()[-2000:],
        }))]

    # ── moma_conflicts_list ──
    elif name == "moma_conflicts_list":
        limit = arguments.get("limit", 20)
        path = storage.root / "index" / "conflicts.json"
        conflicts = []
        if path.exists():
            conflicts = json.loads(path.read_text())
        return [TextContent(type="text", text=json.dumps(conflicts[-limit:], indent=2))]

    # ── moma_graph_stats ──
    elif name == "moma_graph_stats":
        return [TextContent(type="text", text=json.dumps(get_graph_stats(), indent=2))]

    # ── moma_graph_related ──
    elif name == "moma_graph_related":
        concept = arguments["concept"]
        limit = arguments.get("limit", 10)
        mem_ids = get_related_memories(concept, limit=limit)
        memories = [storage.load_memory(mid) for mid in mem_ids]
        memories = [m for m in memories if m]
        return [TextContent(type="text", text=json.dumps(memories, indent=2))]

    # ── moma_team_create ──
    elif name == "moma_team_create":
        cfg = create_team(
            name=arguments["name"],
            description=arguments.get("description", ""),
            members=arguments.get("members", []),
        )
        return [TextContent(type="text", text=json.dumps(cfg))]

    # ── moma_team_save ──
    elif name == "moma_team_save":
        team = arguments["team"]
        visibility = arguments.get("visibility", "shared")
        memory = Memory(
            id=ids.memory_id(),
            type=arguments.get("type", "fact"),
            scope="project",
            project=slugify(team),
            title=arguments["title"],
            content=scrub(arguments["content"]),
            concepts=arguments.get("concepts", []),
            files=[],
            importance=arguments.get("importance", 7),
            confidence=0.9,
            created_at=now,
            updated_at=now,
            session_ids=["mcp-team"],
        )
        save_team_memory(team, memory, visibility=visibility)
        return [TextContent(type="text", text=json.dumps({"saved": True, "id": memory.id, "team": team}))]

    # ── moma_team_search ──
    elif name == "moma_team_search":
        team = arguments["team"]
        query = arguments["query"]
        visibility = arguments.get("visibility", "shared")
        keywords = query.lower().split()
        mems = []
        for vis in (["shared", "private"] if visibility == "both" else [visibility]):
            for m in list_team_memories(team, visibility=vis):
                text = f"{m.get('title','')} {m.get('content','')}".lower()
                if any(kw in text for kw in keywords):
                    mems.append(m)
        return [TextContent(type="text", text=json.dumps(mems, indent=2))]

    # ── moma_teams_list ──
    elif name == "moma_teams_list":
        return [TextContent(type="text", text=json.dumps(list_teams(), indent=2))]

    # ── moma_consolidate ──
    elif name == "moma_consolidate":
        consolidate_script = PROJECT_DIR / "scripts" / "consolidate.py"
        cmd = [sys.executable, str(consolidate_script)]
        project = arguments.get("project", "")
        if project:
            cmd.append(project)
        if arguments.get("dry_run"):
            cmd.append("--dry-run")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=120)
        out = (stdout + stderr).decode()
        try:
            result = json.loads(out)
        except Exception:
            result = {"output": out[-2000:], "exit_code": proc.returncode}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_bridge_pull ──
    elif name == "moma_bridge_pull":
        bridge_script = PROJECT_DIR / "scripts" / "claude_bridge.py"
        proc = subprocess.Popen(
            [sys.executable, str(bridge_script), "pull", arguments["project_dir"]],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=30)
        out = (stdout + stderr).decode()
        try:
            result = json.loads(out)
        except Exception:
            result = {"output": out[-1000:], "exit_code": proc.returncode}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_bridge_push ──
    elif name == "moma_bridge_push":
        bridge_script = PROJECT_DIR / "scripts" / "claude_bridge.py"
        cmd = [sys.executable, str(bridge_script), "push", arguments["project_dir"]]
        if arguments.get("project"):
            cmd.append(arguments["project"])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=30)
        out = (stdout + stderr).decode()
        try:
            result = json.loads(out)
        except Exception:
            result = {"output": out[-1000:], "exit_code": proc.returncode}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_export ──
    elif name == "moma_export":
        export_script = PROJECT_DIR / "scripts" / "export_import.py"
        project = arguments.get("project", "")
        proc = subprocess.Popen(
            [sys.executable, str(export_script), "export", project],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=60)
        out = stdout.decode()
        try:
            result = json.loads(out)
        except Exception:
            result = {"error": stderr.decode()[-500:]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_import ──
    elif name == "moma_import":
        export_script = PROJECT_DIR / "scripts" / "export_import.py"
        bundle_path = arguments["bundle_path"]
        target = arguments.get("target_project", "")
        cmd = [sys.executable, str(export_script), "import", bundle_path]
        if target:
            cmd.append(target)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=60)
        out = stdout.decode()
        try:
            result = json.loads(out)
        except Exception:
            result = {"error": stderr.decode()[-500:]}
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_lease_acquire ──
    elif name == "moma_lease_acquire":
        resource_id = arguments["resource_id"]
        holder = arguments.get("holder", "mcp-client")
        ttl = arguments.get("ttl", 30)
        ok = _leases.acquire(resource_id, holder=holder, ttl=ttl)
        return [TextContent(type="text", text=json.dumps({"ok": ok, "resource_id": resource_id, "holder": holder, "ttl": ttl}))]

    # ── moma_lease_release ──
    elif name == "moma_lease_release":
        resource_id = arguments["resource_id"]
        _leases.release(resource_id)
        return [TextContent(type="text", text=json.dumps({"released": True, "resource_id": resource_id}))]

    # ── moma_leases_list ──
    elif name == "moma_leases_list":
        active = _leases.list_active()
        return [TextContent(type="text", text=json.dumps(active, indent=2))]

    # ── moma_git_snapshot_create ──
    elif name == "moma_git_snapshot_create":
        label = arguments.get("label", "manual")
        result = _snaps.create_snapshot(label=label)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_git_snapshot_list ──
    elif name == "moma_git_snapshot_list":
        limit = arguments.get("limit", 20)
        snaps = _snaps.list_snapshots(limit=limit)
        return [TextContent(type="text", text=json.dumps(snaps, indent=2))]

    # ── moma_git_rollback ──
    elif name == "moma_git_rollback":
        sha = arguments["sha"]
        result = _snaps.rollback_snapshot(sha)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── moma_git_diff ──
    elif name == "moma_git_diff":
        sha1 = arguments["sha1"]
        sha2 = arguments.get("sha2", "HEAD")
        diff = _snaps.diff_snapshots(sha1, sha2)
        return [TextContent(type="text", text=diff)]

    # ── moma_health ──
    elif name == "moma_health":
        issues = []
        summary = {}

        # 1. Count all memory files vs index
        all_mems = storage.list_memories()
        summary["total_memories"] = len(all_mems)

        # 2. Check for corrupt frontmatter
        corrupt = []
        for path in storage.root.rglob("*.md"):
            if "snapshots" in str(path):
                continue
            try:
                text = path.read_text()
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) < 3:
                        corrupt.append(str(path))
            except Exception:
                corrupt.append(str(path))
        if corrupt:
            issues.append({"type": "corrupt_frontmatter", "count": len(corrupt), "files": corrupt[:10]})
        summary["corrupt_files"] = len(corrupt)

        # 3. Check for orphaned observation files (no matching session)
        session_ids = {s["id"] for s in storage.list_sessions()}
        raw_dir = storage.root / "raw"
        orphaned_obs = []
        if raw_dir.exists():
            for f in raw_dir.glob("*.jsonl"):
                sid = f.stem
                if sid not in session_ids:
                    orphaned_obs.append(str(f))
        if orphaned_obs:
            issues.append({"type": "orphaned_observation_files", "count": len(orphaned_obs), "files": orphaned_obs[:10]})
        summary["orphaned_observation_files"] = len(orphaned_obs)

        # 4. Check for stale leases
        stale_leases = []
        import time as _time
        leases_dir = MOMA_ROOT / "locks"
        if leases_dir.exists():
            for lf in leases_dir.glob("*.lock"):
                try:
                    data = json.loads(lf.read_text())
                    age = _time.time() - data.get("acquired_at", 0)
                    if age > data.get("ttl", 30):
                        stale_leases.append(str(lf))
                        lf.unlink(missing_ok=True)
                except Exception:
                    pass
        if stale_leases:
            issues.append({"type": "stale_leases_cleaned", "count": len(stale_leases)})
        summary["stale_leases_cleaned"] = len(stale_leases)

        # 5. Check audit log
        audit = storage.get_audit_log(limit=1)
        summary["audit_log_accessible"] = True if audit is not None else False

        # 6. Storage size
        size_bytes = sum(f.stat().st_size for f in storage.root.rglob("*") if f.is_file())
        summary["storage_kb"] = round(size_bytes / 1024, 1)

        summary["healthy"] = len(issues) == 0
        return [TextContent(type="text", text=json.dumps({"summary": summary, "issues": issues}, indent=2))]

    return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]


# ── MCP Prompts ───────────────────────────────────────────────────────────────

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="recall_context",
            description="Build full memory context for the current project. Use at session start.",
            arguments=[
                PromptArgument(name="project", description="Project name or slug", required=True),
                PromptArgument(name="task", description="What you're about to work on", required=False),
            ],
        ),
        Prompt(
            name="session_handoff",
            description="Generate a handoff summary for the current session — useful when switching agents or resuming tomorrow.",
            arguments=[
                PromptArgument(name="session_id", description="Session ID to summarise", required=True),
            ],
        ),
        Prompt(
            name="detect_patterns",
            description="Analyse memories to detect recurring patterns, anti-patterns, and improvement opportunities.",
            arguments=[
                PromptArgument(name="project", description="Project to analyse", required=True),
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    now = datetime.now(timezone.utc).isoformat()

    if name == "recall_context":
        project = arguments.get("project", "")
        task = arguments.get("task", "")
        config = load_config()
        mems = get_relevant_memories(
            query=task or project,
            project_slug=slugify(project),
            project_files=[],
            max_tokens=config["injection"]["max_tokens"],
        )
        context = format_context(mems, project)
        return types.GetPromptResult(
            description=f"Memory context for {project}",
            messages=[PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"Here is what I remember about {project}:\n\n{context or '(no memories yet)'}\n\nTask: {task or 'general session'}",
                ),
            )],
        )

    elif name == "session_handoff":
        session_id = arguments.get("session_id", "")
        session = storage.load_session(session_id)
        obs = storage.load_observations(session_id)
        compressed = storage.load_compressed(session_id)
        summary = f"Session: {session_id}\n"
        if session:
            summary += f"Project: {session.get('project')}\nAgent: {session.get('agent')}\nStarted: {session.get('started_at')}\n"
            intent = session.get("intent") or {}
            summary += f"Goal: {intent.get('goal') or intent.get('raw') or 'unknown'}\n"
        summary += f"Observations: {len(obs)}\n"
        if compressed:
            summary += f"Memories extracted: {compressed.get('memories_saved', [])}\n"
        return types.GetPromptResult(
            description=f"Session handoff for {session_id}",
            messages=[PromptMessage(
                role="user",
                content=TextContent(type="text", text=f"Summarise this session for handoff:\n\n{summary}"),
            )],
        )

    elif name == "detect_patterns":
        project = arguments.get("project", "")
        mems = storage.list_memories(project_slug=slugify(project))
        concept_freq: dict[str, int] = {}
        for m in mems:
            for c in m.get("concepts", []):
                concept_freq[c] = concept_freq.get(c, 0) + 1
        top = sorted(concept_freq.items(), key=lambda x: x[1], reverse=True)[:15]
        bug_mems = [m for m in mems if m.get("type") == "bug"]
        mem_text = "\n".join(f"- [{m['type']}] {m['title']}: {m['content'][:100]}" for m in mems[:30])
        return types.GetPromptResult(
            description=f"Pattern detection for {project}",
            messages=[PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"Analyse these memories for {project} and identify recurring patterns, anti-patterns, and improvement opportunities:\n\n{mem_text}\n\nTop concepts: {top}\nBug count: {len(bug_mems)}",
                ),
            )],
        )

    return types.GetPromptResult(description="unknown prompt", messages=[])


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    storage.init()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run()
