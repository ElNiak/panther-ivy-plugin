# shellcheck shell=bash
# LSP segment: lsp:ready | lsp:idx 12/40 | lsp:starting | lsp:down | lsp:?
# Reads STC_LSP_* populated by statusline_cache_load().

_STATUSLINE_LSP_STALE_SECONDS="${PANTHER_IVY_STATUSLINE_STALE_SECONDS:-60}"

render_lsp() {
    local status="${STC_LSP_STATUS:-unknown}"
    [ -z "$status" ] && status="unknown"
    local age="${STC_LSP_AGE:-99999}"

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
            color="$C_YELLOW"
            if [ -n "${STC_LSP_IDX_DONE:-}" ] && [ -n "${STC_LSP_IDX_TOTAL:-}" ]; then
                body="idx ${STC_LSP_IDX_DONE}/${STC_LSP_IDX_TOTAL}"
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
