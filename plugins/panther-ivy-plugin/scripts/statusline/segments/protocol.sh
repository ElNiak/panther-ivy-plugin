# shellcheck shell=bash
# Protocol segment: emoji + protocol name in bold white.
# Always present when the cache has a workspace record.

render_protocol() {
    local cache_file="$1"
    local proto
    proto="$(statusline_cache_get "$cache_file" '.workspace.protocol')" || return 0
    printf '%s%s%s%s' "$EMO_PROTOCOL" "$C_BOLD" "$proto" "$C_RESET"
}
