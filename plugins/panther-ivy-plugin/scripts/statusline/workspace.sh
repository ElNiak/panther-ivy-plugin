# shellcheck shell=bash
# Workspace detection for the panther-ivy-plugin statusline.
#
# Exports after detect_statusline_workspace() on success:
#   STATUSLINE_WORKSPACE_ROOT   — absolute path to the panther_ivy directory
#                                 (the parent of protocol-testing/).
#
# Returns 0 if detection succeeded, 1 otherwise.
#
# The cache is keyed on STATUSLINE_WORKSPACE_ROOT. The currently-focused
# protocol and active workflow/test-file are fields inside the cache file
# written by hooks; this script does not need to resolve them to find the
# cache path.

_statusline_find_panther_ivy() {
    local dir="$1"
    local check="$dir"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        local candidate="$check/panther/plugins/services/testers/panther_ivy"
        if [ -d "$candidate/protocol-testing" ]; then
            echo "$candidate"
            return 0
        fi
        if [ -d "$check/protocol-testing" ] && \
           [ "$(basename "$check")" = "panther_ivy" ]; then
            echo "$check"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
    return 1
}

detect_statusline_workspace() {
    STATUSLINE_WORKSPACE_ROOT=""

    local cwd="${1:-$PWD}"
    local panther_ivy
    panther_ivy="$(_statusline_find_panther_ivy "$cwd")" || return 1

    STATUSLINE_WORKSPACE_ROOT="$panther_ivy"
    export STATUSLINE_WORKSPACE_ROOT
    return 0
}

# Resolve the active panther-ivy protocol selection (the value
# `ivy_workspace(action="set", target=...)` writes to
# `<workspace_root>/.ivy-workspace-state.json::active_group`).
#
# Echoes the validated group name (e.g. "bgp", "quic") on stdout, or the
# sentinel "default" when:
#   - the state file is missing
#   - jq is not installed (no JSON parser available)
#   - the file is unreadable / malformed
#   - active_group is null or absent in the JSON
#   - active_group fails the safety regex (must be [A-Za-z0-9_-]+)
#
# This mirrors `statusline_cache._normalize_active_group` so the bash
# renderer and the Python writers agree on the partition key.
resolve_active_group() {
    local workspace_root="${1:-$STATUSLINE_WORKSPACE_ROOT}"
    [ -n "$workspace_root" ] || { echo "default"; return 0; }

    local state_file="$workspace_root/.ivy-workspace-state.json"
    [ -f "$state_file" ] || { echo "default"; return 0; }
    command -v jq >/dev/null 2>&1 || { echo "default"; return 0; }

    local raw
    raw="$(jq -r '.active_group // "default"' "$state_file" 2>/dev/null || echo "default")"
    [ -n "$raw" ] && [ "$raw" != "null" ] || raw="default"

    # Path-safe sanitization: anything outside [A-Za-z0-9_-] collapses to
    # "default" so a malformed state file cannot escape the cache directory.
    if [[ "$raw" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "$raw"
    else
        echo "default"
    fi
}
