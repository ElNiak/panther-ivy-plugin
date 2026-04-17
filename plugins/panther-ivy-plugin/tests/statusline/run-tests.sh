#!/usr/bin/env bash
# Plain-bash test runner for the panther-ivy-plugin statusline.
#
# Each test sets up a fixture cache + fake global statusline, runs main.sh,
# and asserts on the output (ANSI-stripped). No external test framework.
#
# Exit code is the number of failed tests.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MAIN="$PLUGIN_ROOT/scripts/statusline/main.sh"
STDIN_SAMPLE="$SCRIPT_DIR/fixtures/stdin-sample.json"

# Scratch directory inside the worktree (sandbox-friendly).
SCRATCH="$SCRIPT_DIR/.scratch"
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

# Build a fake ivy workspace layout so detect_statusline_workspace() succeeds.
FAKE_IVY="$SCRATCH/fake-repo/panther/plugins/services/testers/panther_ivy"
mkdir -p "$FAKE_IVY/protocol-testing/bgp/.panther-ivy"
echo 'workflow: verify' > "$FAKE_IVY/protocol-testing/bgp/.panther-ivy/active-workflow"
CWD_IN_WS="$FAKE_IVY/protocol-testing/bgp"
sed "s|/tmp/fake-panther/panther/plugins/services/testers/panther_ivy/protocol-testing/bgp|$CWD_IN_WS|" \
    "$STDIN_SAMPLE" > "$SCRATCH/stdin.json"

# Fake global statusline: prints a deterministic line for assertions.
FAKE_GLOBAL="$SCRATCH/fake-global.sh"
cat > "$FAKE_GLOBAL" <<'EOF'
#!/usr/bin/env bash
# Ignore stdin; emit a line that includes whichever CLAUDE_STATUSLINE_ELEMENTS
# we can see, so tests can assert the mode's filter reached us.
cat >/dev/null
echo "GLOBAL[${CLAUDE_STATUSLINE_ELEMENTS:-unset}]"
EOF
chmod +x "$FAKE_GLOBAL"

strip_ansi() {
    # Delete CSI escape sequences.
    sed -E $'s/\x1b\\[[0-9;]*[mKGAB]//g'
}

# iso_offset_now SECONDS → prints ISO8601 timestamp offset by SECONDS seconds.
iso_offset_now() {
    local offset="$1"
    "${TEST_PYTHON:-python3}" - "$offset" <<'PY'
import sys
from datetime import datetime, timezone, timedelta
ts = datetime.now(timezone.utc) + timedelta(seconds=int(sys.argv[1]))
print(ts.isoformat())
PY
}

write_cache() {
    local path="$1"
    local now_iso
    now_iso="$(iso_offset_now 0)"
    cat > "$path" <<EOF
{
  "version": 1,
  "workspace": {"root": "$FAKE_IVY", "protocol": "bgp", "detected_at": "$now_iso"},
  "workflow": {"name": "verify", "phase": "compile", "invocation_depth": 0, "caller": null},
  "mcp": {"status": "up", "pid": 12345, "port": 58123, "last_error": null,
          "last_checked_at": "$now_iso", "latency_ms": 34},
  "lsp": {"status": "ready", "pid": 12346, "indexing": null,
          "last_checked_at": "$now_iso"},
  "test_file": {"basename": "frr_open.ivy", "source": "workflow-focus"}
}
EOF
}

# Global test state.
PASS=0
FAIL=0

# run_case NAME MODE CACHE_PATH EXPECTED_SUBSTRING [UNEXPECTED_SUBSTRING]
run_case() {
    local name="$1" mode="$2" cache="$3" expect="$4" not_expect="${5:-}"
    local output
    output="$(
        NO_COLOR=1 \
        PANTHER_IVY_STATUSLINE_CACHE_PATH="$cache" \
        PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL" \
        PANTHER_IVY_STATUSLINE_MODE="$mode" \
        bash "$MAIN" < "$SCRATCH/stdin.json" 2>/dev/null | strip_ansi
    )" || output="[exit $?]"
    if [[ "$output" != *"$expect"* ]]; then
        FAIL=$((FAIL + 1))
        printf '  FAIL %s\n    expected substring: %s\n    got: %s\n' "$name" "$expect" "$output"
        return
    fi
    if [ -n "$not_expect" ] && [[ "$output" == *"$not_expect"* ]]; then
        FAIL=$((FAIL + 1))
        printf '  FAIL %s\n    should not contain: %s\n    got: %s\n' "$name" "$not_expect" "$output"
        return
    fi
    PASS=$((PASS + 1))
    printf '  ok   %s\n' "$name"
}

# --- Tests ---

echo "# healthy cache, each mode"
write_cache "$SCRATCH/cache-healthy.json"
run_case "suppress-overlaps renders base + ivy segments" \
    "suppress-overlaps" "$SCRATCH/cache-healthy.json" \
    "GLOBAL[git model context files tasks gitextra session diagnostics agents planmode permissions] │ 🐍 bgp · wf:verify:compile · lsp:ready · mcp:up 34ms · test:frr_open.ivy"
run_case "ivy-only skips global script" \
    "ivy-only" "$SCRATCH/cache-healthy.json" \
    "🐍 bgp · wf:verify:compile · lsp:ready · mcp:up 34ms · test:frr_open.ivy" \
    "GLOBAL["
run_case "minimal forwards git model context" \
    "minimal" "$SCRATCH/cache-healthy.json" \
    "GLOBAL[git model context] │ 🐍 bgp"
run_case "full-delegate forwards all" \
    "full-delegate" "$SCRATCH/cache-healthy.json" \
    "GLOBAL[all] │ 🐍 bgp"

echo "# degraded states"
# mcp down fixture
NOW_ISO="$(iso_offset_now 0)"
cat > "$SCRATCH/cache-mcp-down.json" <<EOF
{"version":1,
 "workspace":{"root":"$FAKE_IVY","protocol":"bgp","detected_at":"$NOW_ISO"},
 "workflow":{"name":"verify","phase":"compile","invocation_depth":0,"caller":null},
 "mcp":{"status":"down","last_error":"notification","last_checked_at":"$NOW_ISO"},
 "lsp":{"status":"ready","last_checked_at":"$NOW_ISO"},
 "test_file":{"basename":"frr_open.ivy"}}
EOF
run_case "mcp down renders red down marker" \
    "ivy-only" "$SCRATCH/cache-mcp-down.json" \
    "mcp:down ⚠"

# lsp indexing fixture
cat > "$SCRATCH/cache-lsp-indexing.json" <<EOF
{"version":1,
 "workspace":{"root":"$FAKE_IVY","protocol":"bgp","detected_at":"$NOW_ISO"},
 "workflow":{"name":"build","phase":"propagate","invocation_depth":0,"caller":null},
 "mcp":{"status":"up","latency_ms":18,"last_checked_at":"$NOW_ISO"},
 "lsp":{"status":"indexing","indexing":{"done":12,"total":40},"last_checked_at":"$NOW_ISO"},
 "test_file":null}
EOF
run_case "lsp indexing shows progress counts" \
    "ivy-only" "$SCRATCH/cache-lsp-indexing.json" \
    "lsp:idx 12/40"
run_case "null test_file hides testfile segment" \
    "ivy-only" "$SCRATCH/cache-lsp-indexing.json" \
    "build:propagate" "test:"

# stale fixture (checked 120s ago)
STALE_ISO="$(iso_offset_now -120)"
cat > "$SCRATCH/cache-stale.json" <<EOF
{"version":1,
 "workspace":{"root":"$FAKE_IVY","protocol":"bgp","detected_at":"$NOW_ISO"},
 "workflow":{"name":"verify","phase":"compile","invocation_depth":0,"caller":null},
 "mcp":{"status":"up","latency_ms":34,"last_checked_at":"$STALE_ISO"},
 "lsp":{"status":"ready","last_checked_at":"$STALE_ISO"},
 "test_file":{"basename":"frr_open.ivy"}}
EOF
run_case "stale cache dims mcp/lsp with ? suffix" \
    "ivy-only" "$SCRATCH/cache-stale.json" \
    "lsp:ready?"

# no-workflow fixture
cat > "$SCRATCH/cache-no-workflow.json" <<EOF
{"version":1,
 "workspace":{"root":"$FAKE_IVY","protocol":"bgp","detected_at":"$NOW_ISO"},
 "mcp":{"status":"up","latency_ms":34,"last_checked_at":"$NOW_ISO"},
 "lsp":{"status":"ready","last_checked_at":"$NOW_ISO"},
 "test_file":{"basename":"frr_open.ivy"}}
EOF
run_case "missing workflow renders wf:— dash" \
    "ivy-only" "$SCRATCH/cache-no-workflow.json" \
    "wf:—"

echo "# bootstrap and error paths"
run_case "missing cache shows initializing token" \
    "ivy-only" "$SCRATCH/nonexistent.json" \
    "[ivy: initializing]"

printf 'bad json' > "$SCRATCH/cache-corrupt.json"
run_case "corrupt cache shows cache-error token" \
    "ivy-only" "$SCRATCH/cache-corrupt.json" \
    "[ivy: cache error]"

# Long test filename → truncation
write_cache "$SCRATCH/cache-longfile.json"
"${TEST_PYTHON:-python3}" - "$SCRATCH/cache-longfile.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["test_file"]["basename"] = "this_is_a_very_long_ivy_filename.ivy"
json.dump(d, open(p, "w"))
PY
run_case "long test filenames are truncated with ellipsis" \
    "ivy-only" "$SCRATCH/cache-longfile.json" \
    "test:this_is_a_very_long…"

echo "# outside-workspace delegation"
cat > "$SCRATCH/stdin-outside.json" <<EOF
{"workspace":{"current_dir":"/tmp/no-ivy-here"},"model":{"id":"opus"}}
EOF
output_outside="$(
    NO_COLOR=1 \
    PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL" \
    bash "$MAIN" < "$SCRATCH/stdin-outside.json" 2>/dev/null | strip_ansi
)"
if [[ "$output_outside" == "GLOBAL[unset]" ]]; then
    PASS=$((PASS + 1))
    echo "  ok   outside workspace delegates to global unchanged"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL outside workspace delegates to global unchanged"
    echo "    got: $output_outside"
fi

# --- Budget test ---
echo "# render budget"
write_cache "$SCRATCH/cache-budget.json"
start_ns="$("${TEST_PYTHON:-python3}" -c 'import time; print(time.time_ns())')"
NO_COLOR=1 \
PANTHER_IVY_STATUSLINE_CACHE_PATH="$SCRATCH/cache-budget.json" \
PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL" \
PANTHER_IVY_STATUSLINE_MODE="suppress-overlaps" \
bash "$MAIN" < "$SCRATCH/stdin.json" >/dev/null 2>&1
end_ns="$("${TEST_PYTHON:-python3}" -c 'import time; print(time.time_ns())')"
dur_ms=$(( (end_ns - start_ns) / 1000000 ))
BUDGET_MS="${STATUSLINE_BUDGET_MS:-500}"
if [ "$dur_ms" -lt "$BUDGET_MS" ]; then
    PASS=$((PASS + 1))
    echo "  ok   render under budget (${dur_ms} ms, cap ${BUDGET_MS} ms)"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL render over budget (${dur_ms} ms, expected < ${BUDGET_MS} ms)"
fi

# --- Summary ---
echo
printf 'pass: %d, fail: %d\n' "$PASS" "$FAIL"
exit "$FAIL"
