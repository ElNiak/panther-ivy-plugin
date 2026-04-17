#!/usr/bin/env bash
# panther-ivy-plugin specialized statusline.
#
# Reads the Claude Code statusline JSON on stdin, detects whether the current
# directory is inside an Ivy protocol workspace, and composes the user's
# existing global statusline with plugin-specific Ivy segments.
#
# Modes (PANTHER_IVY_STATUSLINE_MODE):
#   ivy-only           only Ivy segments
#   minimal            git + model + context + Ivy
#   full-delegate      full global output + Ivy
#   suppress-overlaps  global minus dir + Ivy    (default)
#
# Outside an Ivy workspace this script exec's the user's global statusline
# unchanged. Rendering is cache-driven; hooks maintain the cache at
# ~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json .
#
# Exit code is always 0: a non-zero exit would make Claude Code suppress all
# statusline output, hiding healthy segments along with the failed ones.

set -u
trap '_emit_fallback_token' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_STATUSLINE="${PANTHER_IVY_GLOBAL_STATUSLINE:-$HOME/.claude/statusline-command.sh}"

# shellcheck source=colors.sh
source "$SCRIPT_DIR/colors.sh"
# shellcheck source=workspace.sh
source "$SCRIPT_DIR/workspace.sh"
# shellcheck source=cache.sh
source "$SCRIPT_DIR/cache.sh"

# Load segment renderers. Each exports a `render_<name>` function that prints
# its segment or nothing (empty output = hide).
for seg in protocol workflow lsp mcp testfile; do
    # shellcheck source=segments/protocol.sh
    # shellcheck source=segments/workflow.sh
    # shellcheck source=segments/lsp.sh
    # shellcheck source=segments/mcp.sh
    # shellcheck source=segments/testfile.sh
    source "$SCRIPT_DIR/segments/$seg.sh"
done

_log() {
    [ "${PANTHER_IVY_STATUSLINE_DEBUG:-0}" = "1" ] || return 0
    local log_dir="$HOME/.claude/panther-ivy-plugin/logs"
    mkdir -p "$log_dir" 2>/dev/null || return 0
    local log_file="$log_dir/statusline.log"
    printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >> "$log_file" 2>/dev/null || true
    # Rotate at ~1 MB, keep last 2
    if [ -f "$log_file" ]; then
        local size
        size="$(wc -c < "$log_file" 2>/dev/null || echo 0)"
        if [ "$size" -gt 1048576 ]; then
            mv -f "$log_file" "${log_file}.1" 2>/dev/null || true
            [ -f "${log_file}.1" ] && mv -f "${log_file}.1" "${log_file}.2" 2>/dev/null || true
        fi
    fi
}

_emit_fallback_token() {
    echo "${EMO_PROTOCOL}${C_RED}ivy: error${C_RESET}"
    exit 0
}

# Read stdin once so the same JSON can be forwarded to the global script.
INPUT_JSON=""
if [ ! -t 0 ]; then
    INPUT_JSON="$(cat)"
fi

# Extract cwd from the Claude JSON payload (fallback to $PWD).
CWD="$PWD"
if [ -n "$INPUT_JSON" ] && command -v jq >/dev/null 2>&1; then
    cwd_from_json="$(printf '%s' "$INPUT_JSON" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null || true)"
    [ -n "$cwd_from_json" ] && CWD="$cwd_from_json"
fi

# Workspace gate: outside an Ivy workspace, delegate unchanged.
if ! detect_statusline_workspace "$CWD"; then
    if [ -x "$GLOBAL_STATUSLINE" ]; then
        printf '%s' "$INPUT_JSON" | exec "$GLOBAL_STATUSLINE"
    fi
    # No global script available and no Ivy workspace: emit nothing.
    exit 0
fi

# Resolve mode.
MODE="${PANTHER_IVY_STATUSLINE_MODE:-suppress-overlaps}"
case "$MODE" in
    ivy-only|minimal|full-delegate|suppress-overlaps) ;;
    *)
        _log "unknown mode '$MODE', defaulting to suppress-overlaps"
        MODE="suppress-overlaps"
        ;;
esac

_global_elements_for_mode() {
    case "$1" in
        minimal) echo "git model context" ;;
        full-delegate) echo "all" ;;
        suppress-overlaps) echo "git model context files tasks gitextra session diagnostics agents planmode permissions" ;;
        *) echo "" ;;
    esac
}

# Invoke the global statusline subprocess and capture stdout. Returns empty
# string if the global is missing, times out, or errors out.
_invoke_global() {
    local elements="$1"
    [ -n "$elements" ] || return 0
    [ -x "$GLOBAL_STATUSLINE" ] || return 0

    local output
    local timed_out=0
    if command -v timeout >/dev/null 2>&1; then
        output="$(CLAUDE_STATUSLINE_ELEMENTS="$elements" \
            timeout 0.2 "$GLOBAL_STATUSLINE" <<< "$INPUT_JSON" 2>/dev/null)" || timed_out=1
    elif command -v gtimeout >/dev/null 2>&1; then
        output="$(CLAUDE_STATUSLINE_ELEMENTS="$elements" \
            gtimeout 0.2 "$GLOBAL_STATUSLINE" <<< "$INPUT_JSON" 2>/dev/null)" || timed_out=1
    else
        output="$(CLAUDE_STATUSLINE_ELEMENTS="$elements" \
            "$GLOBAL_STATUSLINE" <<< "$INPUT_JSON" 2>/dev/null)" || timed_out=1
    fi

    if [ "$timed_out" -ne 0 ]; then
        _log "global statusline timed out or errored"
        export PANTHER_IVY_STATUSLINE_STALE_MARKER="!"
        return 0
    fi
    printf '%s' "$output"
}

BASE_OUTPUT=""
if [ "$MODE" != "ivy-only" ]; then
    BASE_OUTPUT="$(_invoke_global "$(_global_elements_for_mode "$MODE")")"
fi

# Cache readiness check. If the cache is missing, collapse Ivy to a single
# initialization token — hooks will populate the cache on subsequent turns.
CACHE_FILE="$(statusline_cache_path "$STATUSLINE_WORKSPACE_ROOT")"
IVY_SEGMENTS=""
if ! command -v jq >/dev/null 2>&1; then
    IVY_SEGMENTS="${EMO_PROTOCOL}${C_DIM}[ivy: jq missing]${C_RESET}"
elif [ ! -f "$CACHE_FILE" ]; then
    IVY_SEGMENTS="${EMO_PROTOCOL}${C_DIM}[ivy: initializing]${C_RESET}"
elif ! jq -e . "$CACHE_FILE" >/dev/null 2>&1; then
    IVY_SEGMENTS="${EMO_PROTOCOL}${C_DIM}[ivy: cache error]${C_RESET}"
    _log "cache JSON invalid at $CACHE_FILE"
else
    parts=()
    for render_fn in render_protocol render_workflow render_lsp render_mcp render_testfile; do
        out="$("$render_fn" "$CACHE_FILE" 2>/dev/null || true)"
        [ -n "$out" ] && parts+=("$out")
    done
    # Join with middle-dot separator.
    if [ "${#parts[@]}" -gt 0 ]; then
        IVY_SEGMENTS="${parts[0]}"
        for ((i = 1; i < ${#parts[@]}; i++)); do
            IVY_SEGMENTS="${IVY_SEGMENTS} · ${parts[i]}"
        done
    fi
fi

# Final assembly.
if [ -n "$BASE_OUTPUT" ] && [ -n "$IVY_SEGMENTS" ]; then
    printf '%s │ %s\n' "$BASE_OUTPUT" "$IVY_SEGMENTS"
elif [ -n "$BASE_OUTPUT" ]; then
    printf '%s\n' "$BASE_OUTPUT"
else
    printf '%s\n' "$IVY_SEGMENTS"
fi

exit 0
