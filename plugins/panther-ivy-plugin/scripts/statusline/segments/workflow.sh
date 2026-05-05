# shellcheck shell=bash
# Workflow segment: wf:name[:phase].
# Reads STC_WF_* populated by statusline_cache_load().

render_workflow() {
    local name="${STC_WF_NAME:-}"
    if [ -z "$name" ]; then
        printf '%swf:—%s' "$C_DIM" "$C_RESET"
        return 0
    fi

    local body="${C_BOLD}${name}${C_RESET}"
    if [ -n "${STC_WF_PHASE:-}" ]; then
        body="${body}:${C_CYAN}${STC_WF_PHASE}${C_RESET}"
    fi
    printf 'wf:%s' "$body"
}
