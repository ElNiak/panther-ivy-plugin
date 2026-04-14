#!/usr/bin/env bash
# Shared workspace detection and ivy-lsp resolution functions.
# Sourced by start-ivy-server.sh.

set -euo pipefail

# Resolved once; used by find_panther_ivy and resolve_session_id.
_HOOK_SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/hooks/scripts"

# Find panther_ivy directory by walking up from a starting directory.
# Usage: find_panther_ivy "$PWD"
# Returns: path to panther_ivy directory (with protocol-testing/ inside)
find_panther_ivy() {
    local dir="$1"
    # Delegate to canonical Python implementation in hook_utils.
    local result
    result=$(cd "$dir" && python3 -c \
        "import sys; sys.path.insert(0, '$scripts_dir'); from hook_utils import get_workspace_root; print(get_workspace_root())" \
        2>/dev/null) || true
    if [ -n "$result" ] && [ -d "$result/protocol-testing" ]; then
        echo "$result"
        return 0
    fi
    # Bash fallback (mirrors hook_utils.get_workspace_root algorithm)
    local check="$dir"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        local candidate="$check/panther/plugins/services/testers/panther_ivy"
        if [ -d "$candidate/protocol-testing" ]; then
            echo "$candidate"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
    return 1
}

# Detect Ivy workspace root and type.
# Sets: DETECTED_ROOT, DETECTED_TYPE, panther_ivy_dir
# Usage: detect_ivy_workspace
detect_ivy_workspace() {
    DETECTED_ROOT=""
    DETECTED_TYPE=""

    # 1. Check for PANTHER project structure
    panther_ivy_dir="$(find_panther_ivy "$PWD" 2>/dev/null)" || true

    if [ -n "$panther_ivy_dir" ]; then
        DETECTED_ROOT="$panther_ivy_dir"
        DETECTED_TYPE="panther"
        return 0
    fi

    # 2. Walk up from CWD looking for a directory with >=3 .ivy files
    local check="$PWD"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 8 ]; do
        local ivy_count
        ivy_count=$(find "$check" -maxdepth 2 -name "*.ivy" 2>/dev/null | head -5 | wc -l)
        if [ "$ivy_count" -ge 3 ]; then
            DETECTED_ROOT="$check"
            DETECTED_TYPE="standalone"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done

    # 3. Fallback to CWD
    DETECTED_ROOT="$PWD"
    DETECTED_TYPE="fallback"

    # Canonicalize through symlinks for worktree consistency
    DETECTED_ROOT="$(python3 -c "import os; print(os.path.realpath('$DETECTED_ROOT'))" 2>/dev/null || echo "$DETECTED_ROOT")"
}

# Resolve ivy-lsp source path.
# Priority: IVY_LSP_DEV_ROOT > local submodule (via panther_ivy_dir) > empty (use remote)
# Sets: IVY_LSP_SRC
# Usage: resolve_ivy_lsp_source
resolve_ivy_lsp_source() {
    IVY_LSP_SRC=""

    # 1. Explicit dev root
    if [ -n "${IVY_LSP_DEV_ROOT:-}" ] && [ -d "$IVY_LSP_DEV_ROOT/ivy_lsp" ]; then
        IVY_LSP_SRC="$IVY_LSP_DEV_ROOT"
        return 0
    fi

    # 2. Local submodule (requires panther_ivy_dir to be set by detect_ivy_workspace)
    if [ -n "${panther_ivy_dir:-}" ]; then
        local local_lsp="$panther_ivy_dir/submodules/ivy-lsp"
        if [ -d "$local_lsp/ivy_lsp" ]; then
            IVY_LSP_SRC="$local_lsp"
            return 0
        fi
    fi

    # 3. Walk up from CWD looking for submodules/ivy-lsp/
    local check="$PWD"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        local candidate="$check/panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp"
        if [ -d "$candidate/ivy_lsp" ]; then
            IVY_LSP_SRC="$candidate"
            return 0
        fi
        candidate="$check/submodules/ivy-lsp"
        if [ -d "$candidate/ivy_lsp" ]; then
            IVY_LSP_SRC="$candidate"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
}

# Resolve session ID using the canonical ivy-lsp implementation with bash fallback.
# Usage: resolve_session_id [workspace_root]
resolve_session_id() {
    local ws_root="${1:-${IVY_WORKSPACE_ROOT:-$PWD}}"
    # Delegate to canonical Python implementation in hook_utils.
    local scripts_dir="$_HOOK_SCRIPTS_DIR"
    local result
    result=$(python3 -c \
        "import sys; sys.path.insert(0, '$scripts_dir'); from hook_utils import resolve_session_id; print(resolve_session_id())" \
        2>/dev/null) || true
    if [ -n "$result" ] && [ "$result" != "unknown" ]; then
        echo "$result"
        return 0
    fi
    # Bash fallback for when Python is unavailable
    [ -n "${CLAUDE_SESSION_ID:-}" ] && { echo "$CLAUDE_SESSION_ID"; return 0; }
    [ -n "${CLAUDE_CODE_SESSION_ID:-}" ] && { echo "$CLAUDE_CODE_SESSION_ID"; return 0; }
    [ -n "${IVY_SESSION_ID:-}" ] && { echo "$IVY_SESSION_ID"; return 0; }
    echo "unknown"
}
