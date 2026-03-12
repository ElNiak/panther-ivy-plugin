#!/usr/bin/env bash
# Auto-detect Ivy workspace scope before launching the MCP server.
#
# Detection priority:
#   1. PANTHER project: look for panther_ivy/protocol-testing/ relative to CWD
#   2. Walk up from CWD looking for directories with .ivy files
#   3. Fallback: use CWD
#
# Outputs:
#   - Sets IVY_LSP_INCLUDE_PATHS / IVY_LSP_EXCLUDE_PATHS env vars
#   - Launches ivy_lsp --mcp with --workspace pointing to detected root
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"

log() {
    echo "[ivy-tools] $*" >>"$LOG_FILE"
}

# --- Detection ---

DETECTED_ROOT=""
DETECTED_TYPE=""

# 1. Check for PANTHER project structure
#    Look for panther_ivy with protocol-testing/ inside it
find_panther_ivy() {
    local dir="$1"
    # Direct match: CWD is inside or at panther_ivy
    local candidate="$dir/panther/plugins/services/testers/panther_ivy"
    if [ -d "$candidate/protocol-testing" ]; then
        echo "$candidate"
        return 0
    fi
    # Walk up to find it (handles worktree paths, subdirectory CWDs)
    local check="$dir"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        candidate="$check/panther/plugins/services/testers/panther_ivy"
        if [ -d "$candidate/protocol-testing" ]; then
            echo "$candidate"
            return 0
        fi
        # Maybe CWD is inside panther_ivy itself
        if [ -d "$check/protocol-testing" ] && [ -f "$check/panther_ivy.py" ]; then
            echo "$check"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
    return 1
}

panther_ivy_dir="$(find_panther_ivy "$PWD" 2>/dev/null)" || true

if [ -n "$panther_ivy_dir" ]; then
    DETECTED_ROOT="$panther_ivy_dir"
    DETECTED_TYPE="panther"
    export IVY_LSP_INCLUDE_PATHS="${IVY_LSP_INCLUDE_PATHS:-protocol-testing}"
    export IVY_LSP_EXCLUDE_PATHS="${IVY_LSP_EXCLUDE_PATHS:-submodules,test,doc,examples,notebooks,patches}"
    log "Detected PANTHER project: workspace=$DETECTED_ROOT"
fi

# 2. Walk up from CWD looking for a directory with >=3 .ivy files
if [ -z "$DETECTED_ROOT" ]; then
    check="$PWD"
    depth=0
    while [ "$check" != "/" ] && [ $depth -lt 8 ]; do
        ivy_count=$(find "$check" -maxdepth 2 -name "*.ivy" 2>/dev/null | head -5 | wc -l)
        if [ "$ivy_count" -ge 3 ]; then
            DETECTED_ROOT="$check"
            DETECTED_TYPE="standalone"
            log "Detected standalone ivy project: workspace=$DETECTED_ROOT"
            break
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
fi

# 3. Fallback to CWD
if [ -z "$DETECTED_ROOT" ]; then
    DETECTED_ROOT="$PWD"
    DETECTED_TYPE="fallback"
    log "No ivy project detected, using CWD: workspace=$DETECTED_ROOT"
fi

log "Workspace: $DETECTED_ROOT (type=$DETECTED_TYPE)"
log "Include paths: ${IVY_LSP_INCLUDE_PATHS:-<none>}"
log "Exclude paths: ${IVY_LSP_EXCLUDE_PATHS:-<none>}"

# --- Launch ---

exec uvx \
    --from "git+https://github.com/ElNiak/ivy-lsp[mcp]" \
    ivy_lsp \
    --mcp \
    --workspace "$DETECTED_ROOT" \
    2>>"$LOG_FILE"
