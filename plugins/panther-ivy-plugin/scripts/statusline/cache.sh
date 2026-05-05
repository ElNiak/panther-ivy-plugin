# shellcheck shell=bash
# Cache reader helpers for the panther-ivy-plugin statusline.
#
# statusline_cache_load() fetches every field the segments need in ONE jq
# call and computes staleness for mcp/lsp in ONE python call, leaving the
# segment renderers free of subprocess spawns. Total cost for a healthy
# render drops from ~N×40 ms (ten jq spawns + two python spawns) to ~2×40 ms.

# Resolve the cache path for a (workspace_root, active_group) bucket.
# Priority:
#   1. $PANTHER_IVY_STATUSLINE_CACHE_PATH (test override — short-circuits all path computation)
#   2. $PANTHER_IVY_STATUSLINE_CACHE_ROOT/<hash>/<active_group>/statusline.json (test override)
#   3. ~/.claude/panther-ivy-plugin/cache/<hash>/<active_group>/statusline.json (default)
#
# The active_group component matches the Python writer side
# (statusline_cache.cache_path_for): when the second argument is empty or
# missing, the path falls through to the "default" partition, mirroring
# Python's `_normalize_active_group(None) -> "default"`.
statusline_cache_path() {
    local workspace_root="$1"
    local active_group="${2:-default}"
    if [ -n "${PANTHER_IVY_STATUSLINE_CACHE_PATH:-}" ]; then
        echo "$PANTHER_IVY_STATUSLINE_CACHE_PATH"
        return 0
    fi
    [ -n "$active_group" ] || active_group="default"
    local hash
    hash="$(printf '%s' "$workspace_root" | shasum -a 1 | cut -c1-12)"
    local root="${PANTHER_IVY_STATUSLINE_CACHE_ROOT:-$HOME/.claude/panther-ivy-plugin/cache}"
    echo "$root/$hash/$active_group/statusline.json"
}

# Resolve the per-session overlay path within a (workspace_root, active_group,
# session_id) bucket. The overlay holds session-private statusline state
# (per-session test_file, badge metadata) so two Claude Code windows in the
# same workspace+protocol do not overwrite each other's transient view.
#
# Priority:
#   1. $PANTHER_IVY_STATUSLINE_OVERLAY_PATH (test override)
#   2. <cache_root>/<hash>/<active_group>/sessions/<session_id>/overlay.json
statusline_overlay_path() {
    local workspace_root="$1"
    local session_id="$2"
    local active_group="${3:-default}"
    if [ -n "${PANTHER_IVY_STATUSLINE_OVERLAY_PATH:-}" ]; then
        echo "$PANTHER_IVY_STATUSLINE_OVERLAY_PATH"
        return 0
    fi
    [ -n "$active_group" ] || active_group="default"
    local hash
    hash="$(printf '%s' "$workspace_root" | shasum -a 1 | cut -c1-12)"
    local root="${PANTHER_IVY_STATUSLINE_CACHE_ROOT:-$HOME/.claude/panther-ivy-plugin/cache}"
    echo "$root/$hash/$active_group/sessions/$session_id/overlay.json"
}

# Load all fields from the cache into shell variables. Sets:
#   STC_WS_PROTOCOL
#   STC_WF_NAME, STC_WF_PHASE
#   STC_LSP_STATUS, STC_LSP_IDX_DONE, STC_LSP_IDX_TOTAL, STC_LSP_AGE
#   STC_MCP_STATUS, STC_MCP_LATENCY, STC_MCP_AGE
#   STC_TESTFILE
#
# Missing / null fields become empty strings. Ages become the integer 99999
# sentinel when the timestamp is missing or unparseable.
statusline_cache_load() {
    local cache_file="$1"
    STC_WS_PROTOCOL=""
    STC_WF_NAME=""; STC_WF_PHASE=""
    STC_LSP_STATUS=""; STC_LSP_IDX_DONE=""; STC_LSP_IDX_TOTAL=""; STC_LSP_AGE="99999"
    STC_MCP_STATUS=""; STC_MCP_LATENCY=""; STC_MCP_AGE="99999"
    STC_TESTFILE=""

    command -v jq >/dev/null 2>&1 || return 2

    # Single jq pass extracts every scalar, one field per line. A while-read
    # loop is portable across bash 3.2 (macOS system bash) and 4+ (Linux);
    # mapfile/readarray is 4+ only. Reading line-by-line preserves empty
    # fields that an `IFS=$'\t' read` would otherwise collapse.
    local -a fields=()
    local _line
    while IFS= read -r _line; do
        fields[${#fields[@]}]="$_line"
    done < <(jq -r '
        .workspace.protocol // "",
        (.workflow.name // ""),
        (.workflow.phase // ""),
        (.lsp.status // ""),
        (if (.lsp.indexing.done // null) == null then "" else (.lsp.indexing.done|tostring) end),
        (if (.lsp.indexing.total // null) == null then "" else (.lsp.indexing.total|tostring) end),
        (.lsp.last_checked_at // ""),
        (.mcp.status // ""),
        (if (.mcp.latency_ms // null) == null then "" else (.mcp.latency_ms|tostring) end),
        (.mcp.last_checked_at // ""),
        (.test_file.basename // "")
    ' "$cache_file" 2>/dev/null)
    [ "${#fields[@]}" -ge 11 ] || return 3

    STC_WS_PROTOCOL="${fields[0]}"
    STC_WF_NAME="${fields[1]}"
    STC_WF_PHASE="${fields[2]}"
    STC_LSP_STATUS="${fields[3]}"
    STC_LSP_IDX_DONE="${fields[4]}"
    STC_LSP_IDX_TOTAL="${fields[5]}"
    local lsp_ts="${fields[6]}"
    STC_MCP_STATUS="${fields[7]}"
    STC_MCP_LATENCY="${fields[8]}"
    local mcp_ts="${fields[9]}"
    STC_TESTFILE="${fields[10]}"

    # Ages via one python call. Bash+macOS `date` can't parse ISO8601 with
    # timezone offsets cleanly, so one python subprocess is cheapest.
    if [ -n "$lsp_ts" ] || [ -n "$mcp_ts" ]; then
        local ages
        ages="$(python3 - "$lsp_ts" "$mcp_ts" <<'PY' 2>/dev/null || echo "99999 99999"
import sys
from datetime import datetime, timezone
def age(s):
    if not s:
        return 99999
    try:
        ts = datetime.fromisoformat(s)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(int((datetime.now(timezone.utc) - ts).total_seconds()), 0)
    except Exception:
        return 99999
print(age(sys.argv[1]), age(sys.argv[2]))
PY
)"
        IFS=' ' read -r STC_LSP_AGE STC_MCP_AGE <<< "$ages"
        [ -n "$STC_LSP_AGE" ] || STC_LSP_AGE=99999
        [ -n "$STC_MCP_AGE" ] || STC_MCP_AGE=99999
    fi

    export STC_WS_PROTOCOL \
        STC_WF_NAME STC_WF_PHASE \
        STC_LSP_STATUS STC_LSP_IDX_DONE STC_LSP_IDX_TOTAL STC_LSP_AGE \
        STC_MCP_STATUS STC_MCP_LATENCY STC_MCP_AGE \
        STC_TESTFILE
    return 0
}

# Load session-private overlay fields for the given session_id. Sets:
#   STC_SESSION_TEST_FILE   — overlay's test_file.basename, or "" when absent
#   STC_SESSION_TEST_SOURCE — overlay's test_file.source, or "" when absent
#   STC_SESSION_ACTIVE_SKILL — overlay's active_skill.name, or "" when absent
#
# The overlay is best-effort: missing file, missing jq, or version mismatch
# all leave STC_SESSION_* empty so the segment renderers can fall through
# to the workspace-shared cache values from statusline_cache_load.
statusline_overlay_load() {
    local overlay_file="$1"
    STC_SESSION_TEST_FILE=""
    STC_SESSION_TEST_SOURCE=""
    STC_SESSION_ACTIVE_SKILL=""

    [ -n "$overlay_file" ] || return 0
    [ -f "$overlay_file" ] || return 0
    command -v jq >/dev/null 2>&1 || return 0

    local -a fields=()
    local _line
    while IFS= read -r _line; do
        fields[${#fields[@]}]="$_line"
    done < <(jq -r '
        (.test_file.basename // ""),
        (.test_file.source // ""),
        (.active_skill.name // "")
    ' "$overlay_file" 2>/dev/null)
    [ "${#fields[@]}" -ge 3 ] || return 0

    STC_SESSION_TEST_FILE="${fields[0]}"
    STC_SESSION_TEST_SOURCE="${fields[1]}"
    STC_SESSION_ACTIVE_SKILL="${fields[2]}"

    export STC_SESSION_TEST_FILE STC_SESSION_TEST_SOURCE STC_SESSION_ACTIVE_SKILL
    return 0
}

# Render a `<prefix>:<body>` segment with stale-aware formatting.
# Used by the LSP and MCP segments; `$body` and `$color` are the caller's
# normal output; `$is_stale` switches to dim + the configured stale marker;
# `$suffix` is appended verbatim after the color reset (e.g. the MCP warn
# emoji) and is not included in the stale form.
statusline_render_segment() {
    local prefix="$1"
    local color="$2"
    local body="$3"
    local is_stale="$4"
    local suffix="${5:-}"
    local stale_marker="${STATUSLINE_STALE_MARKER:-?}"
    if [ "$is_stale" = "1" ]; then
        printf '%s%s:%s%s%s' "$C_DIM" "$prefix" "$body" "$stale_marker" "$C_RESET"
    else
        printf '%s:%s%s%s%s' "$prefix" "$color" "$body" "$C_RESET" "$suffix"
    fi
}
