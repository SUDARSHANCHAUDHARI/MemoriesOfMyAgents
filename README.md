# MemoriesOfMyAgents

> Local-first persistent memory for AI coding agents.
> Direct file writes. Zero server in capture path. Zero silent failures.

---

## What it does

AI coding agents forget everything between sessions. You re-explain architecture. You re-discover bugs. You re-teach preferences. Every session starts from zero.

**MemoriesOfMyAgents fixes this.**

It captures what your agents do, compresses it into structured long-term memory at session end, and injects the right context the next time you start. No cloud. No server required. No silent failures.

```
Agent works  →  hooks write directly to files (no server)
Session ends →  1 LLM call extracts 0-5 structured memories
Next session →  relevant memories injected automatically
```

## Why it's different

Every other solution requires a local HTTP server in the capture path. If the server is down, you lose data — silently. MemoriesOfMyAgents hooks write **directly to files**. There is no server between the hook and storage. It cannot fail silently.

| | MemoriesOfMyAgents | Others |
|---|---|---|
| Capture path | Direct file write | HTTP POST to localhost |
| Server down = | Unaffected | Silent data loss |
| Compression | 1 LLM call/session (full context) | 1 LLM call/tool call (no context) |
| Retrieval | BM25 + Ebbinghaus decay + TF-IDF + file overlap, RRF fused | Simple keyword match |
| Context injection | Always-on at session start | Opt-in env flag |
| Dedup | Persistent SHA-256 hash, survives restarts | In-memory, lost on restart |
| Conflict detection | Yes | No |
| Cross-project memory | Yes (global scope) | No |
| Privacy filtering | Scrubs API keys/tokens before LLM | No |
| Citation provenance | Source observation → memory chain | No |
| Knowledge graph | Force-directed, concept nodes + edges | No |
| Team memory | Shared namespaces with per-member private scope | No |
| Multi-agent leases | File-based mutex with TTL auto-expiry | No |
| Git snapshots | Real git commits inside `~/.moma/` for rollback | No |
| Memory consolidation | LLM-powered merge of near-duplicates | No |
| Session replay | Scrubber, 0.5×/1×/2×/4× speed | No |
| Real-time stream | WebSocket + SSE fallback | No |
| GuardLocks | Enforceable rules (block/warn/confirm) | No |
| Export/import | Portable JSON bundles | No |
| MCP tools | 39 | 7 |
| Hooks | 9 | 5 |

## Supported agents

| Agent | Method |
|---|---|
| Claude Code | Native hooks (9) + MCP (39 tools) |
| Claude Desktop | MCP server |
| Cursor | MCP server + `.cursorrules` |
| Windsurf | MCP server + `.windsurfrules` |
| Gemini CLI | MCP server + `GEMINI.md` rules |
| Codex CLI | Hooks |
| Aider | Pre/post-session hooks |
| Continue.dev | MCP server + `.continuerules` |
| Cline | MCP server + `.clinerules` |
| Roo Code | MCP server + `.roorules` |
| GitHub Copilot | Workspace rules injection |
| Kilo Code | MCP server |
| Goose | MCP server |
| OpenCode | MCP server |
| Filesystem watcher | Universal — works for any agent that edits files |

## Install

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/MemoriesOfMyAgents
cd MemoriesOfMyAgents
pip install -e .          # installs moma package into your Python env
bash install.sh           # wires hooks + MCP into your chosen agents
```

Set your Anthropic API key for session compression and consolidation:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional — OpenAI embeddings for vector search upgrade (falls back to TF-IDF otherwise):
```bash
export OPENAI_API_KEY=sk-...
```

## How it works

### Capture (always direct file writes)
```
PostToolUse hook       →  append RawObservation to ~/.moma/raw/{session_id}.jsonl
PostToolUseFailure     →  same, importance=9 (failures always captured)
SessionStart hook      →  create ~/.moma/sessions/{session_id}.json
UserPromptSubmit       →  extract intent + inject relevant memories into prompt
PreToolUse hook        →  evaluate GuardLocks
PreCompact hook        →  record pre-compact event
SubagentStart/Stop     →  track subagent lifecycle
Stop hook              →  trigger async compression (non-blocking)
```

### Compression (1 LLM call at session end)
```
Full session JSONL (privacy-scrubbed) + session intent + existing memory titles
        ↓
Single Claude Haiku call with circuit-breaker retry (1s, 2s, 4s backoff)
        ↓
0-5 structured memories extracted, each with source_observation_ids citation chain
        ↓
SHA-256 dedup check → conflict detection → knowledge graph update
        ↓
Written atomically to ~/.moma/memories/{project}/{type}/{id}.md
```

### Retrieval (4-signal RRF fusion)
```
Query + project + open files
        ↓
BM25 (k1=1.5, b=0.75)          — keyword relevance
Ebbinghaus decay                — recency weighted by importance (high-importance decays slower)
File overlap                    — memories referencing current open files
TF-IDF cosine (or vector)       — semantic similarity, optional OpenAI embeddings
        ↓
Reciprocal Rank Fusion (k=60)  — fuses all 4 ranked lists
        ↓
Token-budget packing → injected into next prompt
```

## Memory types

| Type | Example |
|---|---|
| `architecture` | "JWT auth uses jose in src/middleware/auth.ts" |
| `pattern` | "Always uses Hilt for DI across all Android projects" |
| `preference` | "Prefers KSP over KAPT — KAPT is deprecated" |
| `bug` | "Room migration breaks on config change — clear app data" |
| `workflow` | "Always run ship-check before Play Store release" |
| `procedural` | "To release: bump version → ship-check → tag → push" |
| `fact` | "jose chosen over jsonwebtoken for Vercel Edge compat" |
| `conflict` | Superseded memory — contradicted by newer fact |

Memories have two scopes:
- **`project`** — specific to one codebase (file locations, known bugs)
- **`global`** — applies across all projects (stack preferences, workflow rules)

Global memories are always injected regardless of which project you're in.

## GuardLocks

Enforceable rules — not just reminders.

```json
// ~/.moma/config.json
{
  "guardlocks": [
    {
      "id": "gl_001",
      "name": "No direct main commits",
      "pattern": { "branch": "main|master" },
      "action": "block",
      "message": "Create a feature branch first."
    },
    {
      "id": "gl_002",
      "name": "Confirm before rm -rf",
      "pattern": { "tool": "Bash", "contains": "rm -rf" },
      "action": "warn",
      "message": "Destructive command detected."
    }
  ]
}
```

Actions: `allow` | `warn` | `block` | `confirm`

## Dashboard

```bash
cd dashboard && pnpm dev
# → http://localhost:3000
```

Pages:
- **Home** — store-wide stats
- **Memories** — browse + search all memories
- **Sessions** — session list with ▶ Replay link
- **Replay** — session playback with scrubber, 0.5×/1×/2×/4× speed
- **Search** — BM25-powered full-text search
- **Live** — real-time observation stream (WebSocket primary, SSE fallback)
- **Graph** — force-directed knowledge graph, interactive node selection
- **GuardLocks** — view configured rules
- **Settings** — config editor

### Live WebSocket server
```bash
python3 scripts/ws_server.py        # ws://localhost:7842
```
Pure stdlib — no external dependencies. Dashboard connects automatically.

## MCP tools (39)

### Core memory
| Tool | Description |
|---|---|
| `moma_memory_save` | Save a memory with type, scope, importance |
| `moma_memory_search` | BM25 + Ebbinghaus search |
| `moma_context_build` | Build full ranked context block for a project |
| `moma_memory_forget` | Soft-delete (marks as superseded) |
| `moma_memory_update` | Update content or importance |

### Sessions
| Tool | Description |
|---|---|
| `moma_session_start` | Register a session |
| `moma_session_end` | End session + trigger async compression |
| `moma_sessions_list` | List recent sessions |
| `moma_compress_now` | Force compression for a session |

### Analytics
| Tool | Description |
|---|---|
| `moma_memory_patterns` | Top concepts + type distribution |
| `moma_file_history` | All memories referencing a file |
| `moma_project_profile` | Project summary: top memories, agents, files |
| `moma_stats` | Store-wide stats |

### GuardLocks
| Tool | Description |
|---|---|
| `moma_guardlock_check` | Check if action is allowed (allow/warn/block) |
| `moma_guardlock_list` | List all configured rules |

### Audit & provenance
| Tool | Description |
|---|---|
| `moma_audit_log` | View recent audit events |
| `moma_memory_provenance` | Trace memory → source observations |
| `moma_conflicts_list` | List unresolved memory conflicts |

### Snapshots
| Tool | Description |
|---|---|
| `moma_snapshot_create` | JSON snapshot of full memory store |
| `moma_snapshot_list` | List all snapshots |
| `moma_git_snapshot_create` | Git-versioned snapshot inside `~/.moma/` |
| `moma_git_snapshot_list` | List git snapshots (git log) |
| `moma_git_rollback` | Roll back to a snapshot by commit SHA |
| `moma_git_diff` | Diff between two snapshots |

### Knowledge graph
| Tool | Description |
|---|---|
| `moma_graph_stats` | Node + edge counts, type distribution |
| `moma_graph_related` | Find memories related to a concept |

### Team memory
| Tool | Description |
|---|---|
| `moma_team_create` | Create a shared team namespace |
| `moma_team_save` | Save memory to team namespace |
| `moma_team_search` | Search team memories |
| `moma_teams_list` | List all teams |

### Consolidation & sync
| Tool | Description |
|---|---|
| `moma_consolidate` | LLM-powered merge of near-duplicate memories |
| `moma_bridge_pull` | Import MEMORY.md bullets into moma |
| `moma_bridge_push` | Export top memories to MEMORY.md |
| `moma_export` | Export memories to portable JSON bundle |
| `moma_import` | Import from JSON bundle |

### Multi-agent leases
| Tool | Description |
|---|---|
| `moma_lease_acquire` | Acquire file-based mutex for a resource |
| `moma_lease_release` | Release a lease |
| `moma_leases_list` | List active (non-expired) leases |

### Health
| Tool | Description |
|---|---|
| `moma_health` | Storage integrity check: corrupt files, orphaned observations, stale leases |

## Additional MCP resources (6)

`moma://status` · `moma://memories/latest` · `moma://graph/stats` · `moma://conflicts` · `moma://audit/recent` · `moma://teams`

## MCP prompts (3)

`recall_context` · `session_handoff` · `detect_patterns`

## Utility scripts

```bash
# Universal filesystem watcher (works with any agent)
python3 scripts/fs_watcher.py /path/to/project

# Real-time WebSocket broadcast server
python3 scripts/ws_server.py

# Memory consolidation (merge near-duplicates via LLM)
python3 scripts/consolidate.py [project_slug] [--dry-run]

# MEMORY.md ↔ moma sync
python3 scripts/claude_bridge.py pull /path/to/project
python3 scripts/claude_bridge.py push /path/to/project

# Export/import portable bundles
python3 scripts/export_import.py export [project_slug] > bundle.json
python3 scripts/export_import.py import bundle.json [project_slug]

# Deploy agent rules files to a project
bash scripts/deploy_rules.sh /path/to/project cursor
```

## Storage layout

```
~/.moma/
├── sessions/          # session metadata + intent JSON
├── raw/               # append-only JSONL per session (RawObservations)
├── compressed/        # LLM-compressed session digests
├── memories/
│   ├── global/        # cross-project memories
│   └── {project}/     # project-scoped memories by type
├── index/
│   ├── MEMORY_INDEX.md
│   ├── dedup.json     # persistent SHA-256 dedup
│   ├── embed_cache.json  # optional vector embedding cache
│   └── conflicts.json # contradiction log
├── graph/
│   └── graph.json     # knowledge graph nodes + edges
├── teams/
│   └── {team}/        # team shared + private memory namespaces
├── locks/             # multi-agent lease files
└── config.json
```

## Tech stack

- **Hooks**: Python 3 stdlib — direct file writes, no HTTP in capture path
- **Storage**: Markdown + YAML frontmatter (memories) + JSONL (observations)
- **Retrieval**: Pure Python BM25 + TF-IDF — zero ML dependencies
- **Compression**: Claude Haiku 4.5 — ~$0.001 per session
- **MCP server**: Python `mcp` library, 39 tools + 6 resources + 3 prompts
- **Dashboard**: Next.js 15 + TypeScript + Tailwind CSS
- **WebSocket server**: Pure Python stdlib, no external dependencies
- **No server in capture path. No database. No ORM.**

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

---

Built by [SudarshanTechLabs](https://github.com/SUDARSHANCHAUDHARI)
