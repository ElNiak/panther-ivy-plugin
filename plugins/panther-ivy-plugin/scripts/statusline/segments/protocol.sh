# shellcheck shell=bash
# Protocol segment: emoji + protocol name in bold white.
# Reads STC_WS_PROTOCOL populated by statusline_cache_load().

render_protocol() {
    [ -n "${STC_WS_PROTOCOL:-}" ] || return 0
    printf '%s%s%s%s' "$EMO_PROTOCOL" "$C_BOLD" "$STC_WS_PROTOCOL" "$C_RESET"
}
