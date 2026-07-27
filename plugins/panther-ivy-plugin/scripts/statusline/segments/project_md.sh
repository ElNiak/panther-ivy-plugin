# shellcheck shell=bash
# PROJECT.md Mode/Phase segment: Mode: SCAFFOLD | Phase: 4/10 (core stack)
# Empty when no active workspace, no PROJECT.md, or mode=idle.
#
# Calls the Python script render-mode-phase.py which reads
# protocol-testing/<active_group>/PROJECT.md and renders the rolled-up
# Mode/Phase pair. Per audit Phase 6, always-on by default; quiet when
# the protocol is idle.

render_project_md() {
    local script="$SCRIPT_DIR/render-mode-phase.py"
    [ -x "$script" ] || return 0
    local out
    out="$(python3 "$script" 2>/dev/null)" || return 0
    [ -z "$out" ] && return 0
    printf '%s' "$out"
}
