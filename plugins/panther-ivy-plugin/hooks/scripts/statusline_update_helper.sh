# shellcheck shell=bash
# Shared helper for bash hooks that update the panther-ivy-plugin statusline
# cache. Sourced by wait-for-indexing.sh and check-indexing-ready.sh.
#
# Usage:
#     source "$SCRIPT_DIR/statusline_update_helper.sh"
#     _update_statusline mcp '{"status":"up"}'

_update_statusline() {
    local section="$1"
    local data="$2"
    local dir
    dir="${STATUSLINE_HELPER_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
    python3 "$dir/statusline_cache.py" --auto-workspace \
        --section "$section" --data "$data" 2>/dev/null || true
}
