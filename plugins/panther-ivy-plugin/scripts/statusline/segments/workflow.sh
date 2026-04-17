# shellcheck shell=bash
# Workflow segment: wf:[caller→]name[:phase].
# Dim `wf:—` when no workflow is active. Caller chain capped at 2 hops.

render_workflow() {
    local cache_file="$1"
    local name phase caller depth
    name="$(statusline_cache_get "$cache_file" '.workflow.name')" || name=""
    phase="$(statusline_cache_get "$cache_file" '.workflow.phase')" || phase=""
    caller="$(statusline_cache_get "$cache_file" '.workflow.caller')" || caller=""
    depth="$(statusline_cache_get "$cache_file" '.workflow.invocation_depth')" || depth="0"

    if [ -z "$name" ]; then
        printf '%swf:—%s' "$C_DIM" "$C_RESET"
        return 0
    fi

    local body="${C_BOLD}${name}${C_RESET}"
    if [ "${depth:-0}" != "0" ] && [ -n "$caller" ] && [ "$caller" != "null" ]; then
        body="${caller}→${body}"
    fi
    if [ -n "$phase" ] && [ "$phase" != "null" ]; then
        body="${body}:${C_CYAN}${phase}${C_RESET}"
    fi
    printf 'wf:%s' "$body"
}
