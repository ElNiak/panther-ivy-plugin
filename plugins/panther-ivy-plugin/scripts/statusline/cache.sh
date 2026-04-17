# shellcheck shell=bash
# Cache reader helpers for the panther-ivy-plugin statusline.
#
# The cache file format matches statusline_cache.py. All reads go through jq
# so a single missing file or malformed field only affects one segment.

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

# True (exit 0) if the cache file exists and is valid JSON.
statusline_cache_ready() {
    local path="$1"
    [ -f "$path" ] || return 1
    command -v jq >/dev/null 2>&1 || return 2
    jq -e . "$path" >/dev/null 2>&1
}

# Read a single jq expression from the cache. Prints the result on stdout.
# Prints nothing and returns 1 on jq error or null/empty result.
statusline_cache_get() {
    local path="$1"
    local expr="$2"
    local value
    value="$(jq -r "$expr // empty" "$path" 2>/dev/null)" || return 1
    [ -n "$value" ] || return 1
    echo "$value"
}

# Seconds since the given ISO8601 timestamp, or a very large sentinel if the
# timestamp is missing/unparseable. Used for staleness checks.
statusline_age_seconds() {
    local iso="$1"
    [ -n "$iso" ] || { echo 99999; return 0; }
    python3 - "$iso" <<'PY' 2>/dev/null || echo 99999
import sys
from datetime import datetime, timezone
try:
    ts = datetime.fromisoformat(sys.argv[1])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    print(int(max(age, 0)))
except Exception:
    print(99999)
PY
}
