#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up MemoriesOfMyAgents..."

# Create ~/.moma structure
python3 - <<EOF
import sys
sys.path.insert(0, "$PROJECT_DIR")
from moma import Storage
s = Storage()
s.init()
print("  ~/.moma/ structure created")
EOF

# Write default config if missing
python3 - <<EOF
import sys, json
sys.path.insert(0, "$PROJECT_DIR")
from moma.config import MOMA_ROOT, DEFAULTS, save, load
config = load()
save(config)
print(f"  config written to {MOMA_ROOT}/config.json")
EOF

echo ""
echo "Done. ~/.moma/ is ready."
echo ""
echo "Next: run Phase 2 to install hooks."
