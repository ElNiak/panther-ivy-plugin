# shellcheck shell=bash
# Session badge: 4-char colored marker derived from the Claude Code session_id.
#
# Two Claude Code windows in the same workspace+protocol see the same
# shared segments (workflow, mcp, lsp) by design — the workflow is
# workspace-scoped, the MCP server is workspace-scoped. The session badge
# answers "which of my windows is this?" without changing any shared state.
#
# Derivation:
#   - badge text = last 4 chars of session_id (e.g. "3ca0" for the UUID
#     "00893aaf-19fa-41d2-8238-13269b9b3ca0")
#   - color is one of 6 (red/green/yellow/blue/magenta/cyan), picked
#     deterministically from the first hex byte of session_id so the same
#     session always gets the same color across renders
#
# Renders nothing when:
#   - $STATUSLINE_SESSION_ID is empty (smoke-test / CLI invocation)
#   - $STATUSLINE_SESSION_ID is shorter than 4 chars (defensive)

render_session() {
    local sid="${STATUSLINE_SESSION_ID:-}"
    [ -n "$sid" ] || return 0
    [ "${#sid}" -ge 4 ] || return 0

    local badge="${sid: -4}"

    # Deterministic 6-color palette from the first hex byte of the UUID.
    # Treats the leading two hex chars as a number 0..255 mod 6. Skips
    # bright variants to avoid clashing with the workflow / lsp / mcp
    # segment colors that share this palette.
    local first_byte="${sid:0:2}"
    local color_index=0
    if [[ "$first_byte" =~ ^[0-9a-fA-F]{2}$ ]]; then
        # printf %d converts hex to decimal; modulo 6 picks one of six.
        color_index=$(( 0x$first_byte % 6 ))
    fi

    local color
    case "$color_index" in
        0) color="$C_RED" ;;
        1) color="$C_GREEN" ;;
        2) color="$C_YELLOW" ;;
        3) color="$C_CYAN" ;;
        4) color="$C_BOLD" ;;       # bold-only when fewer than 6 ANSI hues are available
        5) color="$C_WHITE" ;;
        *) color="$C_DIM" ;;
    esac

    printf '%sS:%s%s' "$color" "$badge" "$C_RESET"
}
