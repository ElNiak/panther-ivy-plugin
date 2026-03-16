#!/usr/bin/env bash
# Shared workspace detection and ivy-lsp resolution functions.
# Sourced by start-ivy-tools.sh, ivy-lsp-wrapper.sh, and detect-ivy-workspace.sh.

set -euo pipefail

# Find panther_ivy directory by walking up from a starting directory.
# Usage: find_panther_ivy "$PWD"
# Returns: path to panther_ivy directory (with protocol-testing/ inside)
find_panther_ivy() {
    local dir="$1"
    # Direct match: standard PANTHER project structure
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
