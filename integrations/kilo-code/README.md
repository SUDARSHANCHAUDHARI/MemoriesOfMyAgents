# Kilo Code Integration

Uses Kilo Code's MCP server support (same format as Cline).

## Install

```bash
bash integrations/kilo-code/install.sh
```

## Verify

1. VS Code → Kilo Code panel → MCP Servers
2. `moma` should appear as connected
3. Test: ask Kilo Code to call `moma_context_build`

## Rules

```bash
cp integrations/cline/rules.md /path/to/project/.kilorules
```

## Available tools (20)

moma_memory_save, moma_memory_search, moma_context_build, moma_memory_forget,
moma_memory_update, moma_session_start, moma_session_end, moma_sessions_list,
moma_memory_patterns, moma_file_history, moma_project_profile, moma_stats,
moma_guardlock_check, moma_guardlock_list, moma_audit_log, moma_memory_provenance,
moma_snapshot_create, moma_snapshot_list, moma_compress_now, moma_conflicts_list
