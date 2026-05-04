# shellcheck shell=bash
# Protocol segment: emoji + protocol name in bold white.
#
# Reads STC_PROTOCOL (preferred) — the explicit ivy_workspace selection
# resolved from .ivy-workspace-state.json by main.sh. Falls back to
# STC_WS_PROTOCOL (the cache-side "last seen" memo written by
# notify-workspace-change.py to the default partition) when STC_PROTOCOL
# is empty, so a session that has not called ivy_workspace(set) but has
# previous notify-workspace-change history still shows something.
#
# Both empty → segment hidden.

render_protocol() {
    local protocol="${STC_PROTOCOL:-}"
    [ -n "$protocol" ] || protocol="${STC_WS_PROTOCOL:-}"
    [ -n "$protocol" ] || return 0
    printf '%s%s%s%s' "$EMO_PROTOCOL" "$C_BOLD" "$protocol" "$C_RESET"
}
