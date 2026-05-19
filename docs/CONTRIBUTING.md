# Contributing

## Setup

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/MemoriesOfMyAgents
cd MemoriesOfMyAgents
python3.13 -m venv .venv
.venv/bin/pip install mcp
cd dashboard && pnpm install
```

## Project structure

```
moma/           core Python library (types, storage, config, ids)
hooks/          Claude Code hook scripts
scripts/        compression pipeline, search, setup
mcp_server/     MCP server (7 tools)
dashboard/      Next.js dashboard
integrations/   per-agent install scripts and configs
docs/           documentation
```

## Rules

- No server in the capture path — hooks must write directly to files
- All hook errors go to stderr, never swallow silently
- All file writes must be atomic (write .tmp → rename)
- Output truncation must keep the LAST N chars, not the first
- Dedup must be file-based and survive restarts
- Context injection must be always-on — never require an env flag

## Adding a new agent integration

1. Create `integrations/{agent-name}/`
2. Add `install.sh` — wires hooks or writes MCP config
3. Add `mcp.json` if the agent supports MCP
4. Add `README.md` — how to install and verify

## Adding a new MCP tool

1. Add tool definition to `mcp_server/server.py` → `list_tools()`
2. Add handler in `call_tool()`
3. Document in main README MCP tools table

## Testing hooks manually

```bash
# Simulate SessionStart
echo '{"session_id":"ses_test","cwd":"/tmp/testproject"}' | python3 hooks/session_start.py

# Simulate PostToolUse
echo '{"session_id":"ses_test","tool_name":"Edit","tool_input":{},"tool_output":"done"}' | python3 hooks/post_tool_use.py

# Check what was written
cat ~/.moma/sessions/ses_test.json
cat ~/.moma/raw/ses_test.jsonl
```
