# shellcheck shell=bash
# Cache reader helpers for the panther-ivy-plugin statusline.
#
# statusline_cache_load() fetches every field the segments need in ONE jq
# call and computes staleness for mcp/lsp in ONE python call, leaving the
# segment renderers free of subprocess spawns. Total cost for a healthy
# render drops from ~N×40 ms (ten jq spawns + two python spawns) to ~2×40 ms.

# Resolve the cache path for the current workspace.
# Priority:
#   1. $PANTHER_IVY_STATUSLINE_CACHE_PATH (test override)
#   2. $PANTHER_IVY_STATUSLINE_CACHE_ROOT/<hash>/statusline.json (test override)
#   3. ~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json (default)
statusline_cache_path() {
    local workspace_root="$1"
    if [ -n "${PANTHER_IVY_STATUSLINE_CACHE_PATH:-}" ]; then
        echo "$PANTHER_IVY_STATUSLINE_CACHE_PATH"
        return 0
    fi
    local hash
    hash="$(printf '%s' "$workspace_root" | shasum -a 1 | cut -c1-12)"
    local root="${PANTHER_IVY_STATUSLINE_CACHE_ROOT:-$HOME/.claude/panther-ivy-plugin/cache}"
    echo "$root/$hash/statusline.json"
}

# Load all fields from the cache into shell variables. Sets:
#   STC_WS_PROTOCOL
#   STC_WF_NAME, STC_WF_PHASE, STC_WF_CALLER, STC_WF_DEPTH
#   STC_LSP_STATUS, STC_LSP_IDX_DONE, STC_LSP_IDX_TOTAL, STC_LSP_AGE
#   STC_MCP_STATUS, STC_MCP_LATENCY, STC_MCP_AGE
#   STC_TESTFILE
#
# Missing / null fields become empty strings. Ages become the integer 99999
# sentinel when the timestamp is missing or unparseable.
statusline_cache_load() {
    local cache_file="$1"
    STC_WS_PROTOCOL=""
    STC_WF_NAME=""; STC_WF_PHASE=""; STC_WF_CALLER=""; STC_WF_DEPTH="0"
    STC_LSP_STATUS=""; STC_LSP_IDX_DONE=""; STC_LSP_IDX_TOTAL=""; STC_LSP_AGE="99999"
    STC_MCP_STATUS=""; STC_MCP_LATENCY=""; STC_MCP_AGE="99999"
    STC_TESTFILE=""

    [ -f "$cache_file" ] || return 1
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
        (if (.workflow.caller // null) == null then "" else (.workflow.caller|tostring) end),
        (.workflow.invocation_depth // 0 | tostring),
        (.lsp.status // ""),
        (if (.lsp.indexing.done // null) == null then "" else (.lsp.indexing.done|tostring) end),
        (if (.lsp.indexing.total // null) == null then "" else (.lsp.indexing.total|tostring) end),
        (.lsp.last_checked_at // ""),
        (.mcp.status // ""),
        (if (.mcp.latency_ms // null) == null then "" else (.mcp.latency_ms|tostring) end),
        (.mcp.last_checked_at // ""),
        (.test_file.basename // "")
    ' "$cache_file" 2>/dev/null)
    [ "${#fields[@]}" -ge 13 ] || return 3

    STC_WS_PROTOCOL="${fields[0]}"
    STC_WF_NAME="${fields[1]}"
    STC_WF_PHASE="${fields[2]}"
    STC_WF_CALLER="${fields[3]}"
    STC_WF_DEPTH="${fields[4]:-0}"
    STC_LSP_STATUS="${fields[5]}"
    STC_LSP_IDX_DONE="${fields[6]}"
    STC_LSP_IDX_TOTAL="${fields[7]}"
    local lsp_ts="${fields[8]}"
    STC_MCP_STATUS="${fields[9]}"
    STC_MCP_LATENCY="${fields[10]}"
    local mcp_ts="${fields[11]}"
    STC_TESTFILE="${fields[12]}"

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
        STC_WF_NAME STC_WF_PHASE STC_WF_CALLER STC_WF_DEPTH \
        STC_LSP_STATUS STC_LSP_IDX_DONE STC_LSP_IDX_TOTAL STC_LSP_AGE \
        STC_MCP_STATUS STC_MCP_LATENCY STC_MCP_AGE \
        STC_TESTFILE
    return 0
}

# True (exit 0) if the cache file exists and is valid JSON. Kept for
# main.sh's bootstrap check; renderers use the loaded STC_* vars instead.
statusline_cache_ready() {
    local path="$1"
    [ -f "$path" ] || return 1
    command -v jq >/dev/null 2>&1 || return 2
    jq -e . "$path" >/dev/null 2>&1
}
