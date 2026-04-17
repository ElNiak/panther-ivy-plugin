# shellcheck shell=bash
# LSP segment: lsp:ready | lsp:idx 12/40 | lsp:starting | lsp:down | lsp:?
# Dims to `lsp:<state>?` (or `!` if main.sh set a timeout marker) when the
# cached `last_checked_at` is older than 60 seconds.

_STATUSLINE_LSP_STALE_SECONDS="${PANTHER_IVY_STATUSLINE_STALE_SECONDS:-60}"

render_lsp() {
    local cache_file="$1"
    local status checked_at age done_count total
    status="$(statusline_cache_get "$cache_file" '.lsp.status')" || status="unknown"
    checked_at="$(statusline_cache_get "$cache_file" '.lsp.last_checked_at')" || checked_at=""
    age="$(statusline_age_seconds "$checked_at")"

    local stale_marker="${PANTHER_IVY_STATUSLINE_STALE_MARKER:-?}"
    local is_stale=0
    if [ "$status" != "unknown" ] && [ "$age" -gt "$_STATUSLINE_LSP_STALE_SECONDS" ]; then
        is_stale=1
    fi

    local color="" body=""
    case "$status" in
        ready)
            color="$C_GREEN"; body="ready" ;;
        indexing)
            done_count="$(statusline_cache_get "$cache_file" '.lsp.indexing.done')" || done_count=""
            total="$(statusline_cache_get "$cache_file" '.lsp.indexing.total')" || total=""
            color="$C_YELLOW"
            if [ -n "$done_count" ] && [ -n "$total" ]; then
                body="idx ${done_count}/${total}"
            else
                body="indexing"
            fi
            ;;
        starting)
            color="$C_YELLOW"; body="starting" ;;
        down)
            color="$C_RED"; body="down" ;;
        *)
            color="$C_DIM"; body="?" ;;
    esac

    if [ "$is_stale" = "1" ]; then
        printf '%slsp:%s%s%s' "$C_DIM" "$body" "$stale_marker" "$C_RESET"
    else
        printf 'lsp:%s%s%s' "$color" "$body" "$C_RESET"
    fi
}
