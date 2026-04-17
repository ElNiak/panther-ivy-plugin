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
