# shellcheck shell=bash
# MCP segment: mcp:up 34ms | mcp:degraded | mcp:down ⚠ | mcp:?
# Staleness rules match the LSP segment.

_STATUSLINE_MCP_STALE_SECONDS="${PANTHER_IVY_STATUSLINE_STALE_SECONDS:-60}"

render_mcp() {
    local cache_file="$1"
    local status checked_at age latency
    status="$(statusline_cache_get "$cache_file" '.mcp.status')" || status="unknown"
    checked_at="$(statusline_cache_get "$cache_file" '.mcp.last_checked_at')" || checked_at=""
    latency="$(statusline_cache_get "$cache_file" '.mcp.latency_ms')" || latency=""
    age="$(statusline_age_seconds "$checked_at")"

    local stale_marker="${PANTHER_IVY_STATUSLINE_STALE_MARKER:-?}"
    local is_stale=0
    if [ "$status" != "unknown" ] && [ "$age" -gt "$_STATUSLINE_MCP_STALE_SECONDS" ]; then
        is_stale=1
    fi

    local color="" body="" suffix=""
    case "$status" in
        up)
            color="$C_GREEN"; body="up"
            if [ -n "$latency" ] && [ "$latency" != "null" ]; then
                body="up ${latency}ms"
            fi
            ;;
        degraded)
            color="$C_YELLOW"; body="degraded" ;;
        down)
            color="$C_RED"; body="down"; suffix=" $EMO_WARN" ;;
        *)
            color="$C_DIM"; body="?" ;;
    esac

    if [ "$is_stale" = "1" ]; then
        printf '%smcp:%s%s%s' "$C_DIM" "$body" "$stale_marker" "$C_RESET"
    else
        printf 'mcp:%s%s%s%s' "$color" "$body" "$C_RESET" "$suffix"
    fi
}
