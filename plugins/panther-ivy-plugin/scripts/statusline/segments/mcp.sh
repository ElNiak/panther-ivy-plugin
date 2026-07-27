# shellcheck shell=bash
# MCP segment: mcp:up 34ms | mcp:degraded | mcp:down ⚠ | mcp:?
# Reads STC_MCP_* populated by statusline_cache_load().

_STATUSLINE_MCP_STALE_SECONDS="${PANTHER_IVY_STATUSLINE_STALE_SECONDS:-60}"

render_mcp() {
    local status="${STC_MCP_STATUS:-unknown}"
    [ -z "$status" ] && status="unknown"
    local age="${STC_MCP_AGE:-99999}"

    local is_stale=0
    if [ "$status" != "unknown" ] && [ "$age" -gt "$_STATUSLINE_MCP_STALE_SECONDS" ]; then
        is_stale=1
    fi

    local color="" body="" suffix=""
    case "$status" in
        up)
            color="$C_GREEN"; body="up"
            if [ -n "${STC_MCP_LATENCY:-}" ]; then
                body="up ${STC_MCP_LATENCY}ms"
            fi
            ;;
        starting|degraded)
            color="$C_YELLOW"; body="$status" ;;
        down)
            color="$C_RED"; body="down"; suffix=" $EMO_WARN" ;;
        *)
            color="$C_DIM"; body="?" ;;
    esac

    statusline_render_segment "mcp" "$color" "$body" "$is_stale" "$suffix"
}
