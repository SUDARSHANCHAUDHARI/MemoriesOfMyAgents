#!/usr/bin/env bash
# Deploy moma agent rules to a project directory.
# Usage: bash scripts/deploy_rules.sh <agent> <project_dir>
# Agents: cursor, windsurf, gemini-cli, continue, cline, roo-code
#
# cursor    → <project>/.cursorrules
# windsurf  → <project>/.windsurfrules
# gemini    → <project>/GEMINI.md
# continue  → <project>/.continuerules
# cline     → <project>/.clinerules
# roo-code  → <project>/.roorules

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENT="${1:-}"
TARGET="${2:-$(pwd)}"

usage() {
    echo "Usage: bash scripts/deploy_rules.sh <agent> [project_dir]"
    echo "Agents: cursor, windsurf, gemini-cli, continue, cline, roo-code"
    exit 1
}

[ -z "$AGENT" ] && usage
[ ! -d "$TARGET" ] && { echo "ERROR: $TARGET does not exist"; exit 1; }

TARGET="$(cd "$TARGET" && pwd)"

case "$AGENT" in
    cursor)
        SRC="$PROJECT_DIR/integrations/cursor/rules.md"
        DEST="$TARGET/.cursorrules"
        ;;
    windsurf)
        SRC="$PROJECT_DIR/integrations/windsurf/rules.md"
        DEST="$TARGET/.windsurfrules"
        ;;
    gemini|gemini-cli)
        SRC="$PROJECT_DIR/integrations/gemini-cli/rules.md"
        DEST="$TARGET/GEMINI.md"
        ;;
    continue)
        SRC="$PROJECT_DIR/integrations/continue/rules.md"
        DEST="$TARGET/.continuerules"
        ;;
    cline)
        SRC="$PROJECT_DIR/integrations/cline/rules.md"
        DEST="$TARGET/.clinerules"
        ;;
    roo|roo-code)
        SRC="$PROJECT_DIR/integrations/roo-code/rules.md"
        DEST="$TARGET/.roorules"
        ;;
    *)
        echo "Unknown agent: $AGENT"
        usage
        ;;
esac

if [ -f "$DEST" ]; then
    # Append if not already present
    if grep -q "MemoriesOfMyAgents" "$DEST" 2>/dev/null; then
        echo "moma rules already in $DEST — skipping"
        exit 0
    fi
    echo "" >> "$DEST"
    cat "$SRC" >> "$DEST"
    echo "Appended moma rules to $DEST"
else
    cp "$SRC" "$DEST"
    echo "Created $DEST"
fi
