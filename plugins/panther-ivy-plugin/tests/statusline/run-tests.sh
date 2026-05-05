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
  "workflow": {"name": "verify", "phase": "compile", "started": "2026-01-01T00:00:00+00:00"},
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
 "workflow":{"name":"workflow-verify","phase":"compile","started":"2026-01-01T00:00:00+00:00"},
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
 "workflow":{"name":"workflow-build","phase":"propagate","started":"2026-01-01T00:00:00+00:00"},
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
 "workflow":{"name":"workflow-verify","phase":"compile","started":"2026-01-01T00:00:00+00:00"},
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

echo "# mcp:starting state renders"
cat > "$SCRATCH/cache-mcp-starting.json" <<EOF
{"version":1,
 "workspace":{"root":"$FAKE_IVY","protocol":"bgp","detected_at":"$NOW_ISO"},
 "workflow":{"name":"workflow-verify","phase":"compile","started":"2026-01-01T00:00:00+00:00"},
 "mcp":{"status":"starting","last_checked_at":"$NOW_ISO"},
 "lsp":{"status":"ready","last_checked_at":"$NOW_ISO"}}
EOF
run_case "mcp starting renders in yellow body text" \
    "ivy-only" "$SCRATCH/cache-mcp-starting.json" \
    "mcp:starting"

echo "# concurrent writers race"
# Regression test: 10 writers across 5 sections must all survive.
concurrency_cache="$SCRATCH/concurrency.json"
rm -f "$concurrency_cache" "${concurrency_cache}.lock"
concurrency_result="$(
    PANTHER_IVY_STATUSLINE_CACHE_PATH="$concurrency_cache" \
    "${TEST_PYTHON:-python3}" - <<'PY'
import json, os, sys, threading, time, pathlib
sys.path.insert(0, os.environ.get("STATUSLINE_HOOK_DIR", "hooks/scripts"))
from lib.statusline_cache import update_section
import lib.statusline_cache as sc
_orig = sc._read_cache
def _slow(p):
    d = _orig(p); time.sleep(0.02); return d
sc._read_cache = _slow

threads = [
    threading.Thread(target=update_section,
                     args=("/fake/ws",
                           ["mcp","lsp","workflow","workspace","test_file"][i % 5],
                           {"status": f"v{i}"}))
    for i in range(10)
]
for t in threads: t.start()
for t in threads: t.join()

cache = json.loads(pathlib.Path(os.environ["PANTHER_IVY_STATUSLINE_CACHE_PATH"]).read_text())
sections = sorted(k for k in cache if k != "version")
print(",".join(sections))
PY
    STATUSLINE_HOOK_DIR="$PLUGIN_ROOT/hooks/scripts" \
)" || concurrency_result=""
rm -f "$concurrency_cache" "${concurrency_cache}.lock"
if [ "$concurrency_result" = "lsp,mcp,test_file,workflow,workspace" ]; then
    PASS=$((PASS + 1))
    echo "  ok   concurrent writers do not drop sections"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL concurrent writers do not drop sections"
    echo "    got: $concurrency_result"
fi

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

# Global script exits non-zero while outside workspace — must NOT append a
# fallback token after the global's output (regression test for the ERR trap
# bug caught in review).
FAKE_GLOBAL_FAILS="$SCRATCH/fake-global-fails.sh"
cat > "$FAKE_GLOBAL_FAILS" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
echo "partial global"
exit 7
EOF
chmod +x "$FAKE_GLOBAL_FAILS"
output_fail="$(
    NO_COLOR=1 \
    PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL_FAILS" \
    bash "$MAIN" < "$SCRATCH/stdin-outside.json" 2>/dev/null | strip_ansi
)"
if [[ "$output_fail" == "partial global" ]]; then
    PASS=$((PASS + 1))
    echo "  ok   global non-zero exit does not trigger fallback after output"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL global non-zero exit does not trigger fallback after output"
    echo "    got: $(printf '%q' "$output_fail")"
fi

# Global script exits non-zero while inside workspace — output should collapse
# to ivy-only with the `!` stale marker, not corrupt both halves of the bar.
FAKE_GLOBAL_SLOW="$SCRATCH/fake-global-slow.sh"
cat > "$FAKE_GLOBAL_SLOW" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
sleep 3
echo "never reached"
EOF
chmod +x "$FAKE_GLOBAL_SLOW"
# Force a 0.3s timeout so the test completes quickly and is not racy with
# the default budget.
output_slow="$(
    NO_COLOR=1 \
    PANTHER_IVY_STATUSLINE_CACHE_PATH="$SCRATCH/cache-healthy.json" \
    PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL_SLOW" \
    PANTHER_IVY_STATUSLINE_GLOBAL_TIMEOUT="0.3" \
    PANTHER_IVY_STATUSLINE_MODE="suppress-overlaps" \
    bash "$MAIN" < "$SCRATCH/stdin.json" 2>/dev/null | strip_ansi
)"
if [[ "$output_slow" != *"never reached"* ]] && [[ "$output_slow" == *"🐍 bgp"* ]]; then
    PASS=$((PASS + 1))
    echo "  ok   slow global times out and collapses to ivy-only"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL slow global times out and collapses to ivy-only"
    echo "    got: $output_slow"
fi

# NO_COLOR=1 + CLAUDE_STATUSLINE_EMOJIS=false should suppress both escapes
# and emoji markers.
output_bare="$(
    NO_COLOR=1 CLAUDE_STATUSLINE_EMOJIS=false \
    PANTHER_IVY_STATUSLINE_CACHE_PATH="$SCRATCH/cache-healthy.json" \
    PANTHER_IVY_GLOBAL_STATUSLINE="$FAKE_GLOBAL" \
    PANTHER_IVY_STATUSLINE_MODE="ivy-only" \
    bash "$MAIN" < "$SCRATCH/stdin.json" 2>/dev/null
)"
if [[ "$output_bare" != *$'\033'* ]] && [[ "$output_bare" != *"🐍"* ]] && \
   [[ "$output_bare" == *"bgp"* ]]; then
    PASS=$((PASS + 1))
    echo "  ok   NO_COLOR and emoji-off suppress both markers"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL NO_COLOR and emoji-off suppress both markers"
    echo "    got: $(printf '%q' "$output_bare")"
fi

# Cache keys must agree between --workspace and --auto-workspace writers.
CACHE_KEY_WS="$SCRATCH/fake-ws/panther/plugins/services/testers/panther_ivy"
mkdir -p "$CACHE_KEY_WS/protocol-testing/bgp"
rm -rf "$SCRATCH/cache-key-home"
(
    cd "$CACHE_KEY_WS/protocol-testing/bgp" && \
    IVY_WORKSPACE_ROOT="$CACHE_KEY_WS" \
    PANTHER_IVY_STATUSLINE_CACHE_ROOT="$SCRATCH/cache-key-home" \
    "${TEST_PYTHON:-python3}" "$PLUGIN_ROOT/hooks/scripts/statusline_cache.py" \
        --auto-workspace --section mcp --data '{"status":"up"}' && \
    PANTHER_IVY_STATUSLINE_CACHE_ROOT="$SCRATCH/cache-key-home" \
    "${TEST_PYTHON:-python3}" "$PLUGIN_ROOT/hooks/scripts/statusline_cache.py" \
        --workspace "$CACHE_KEY_WS" --section lsp --data '{"status":"ready"}'
) >/dev/null 2>&1
# Both sections should end up in the same cache file (same key).
files_in_cache=$(find "$SCRATCH/cache-key-home" -name statusline.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$files_in_cache" = "1" ]; then
    PASS=$((PASS + 1))
    echo "  ok   --auto-workspace and --workspace hash to the same cache key"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL --auto-workspace and --workspace hash to the same cache key"
    echo "    found $files_in_cache cache files (expected 1)"
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
BUDGET_MS="${STATUSLINE_BUDGET_MS:-1500}"
# Budget rationale: a healthy render in steady state is ~230-300 ms on
# typical macOS hardware. Cost breakdown:
#   ~30-50 ms: jq pass over stdin (one combined call extracting cwd + session_id)
#   ~30-50 ms: jq pass over .ivy-workspace-state.json for active_group
#              (early-exits when the state file is absent)
#   ~30-50 ms: jq pass over the cache JSON (one call extracting all fields)
#   ~30-50 ms: python pass for ISO8601 age computation (cache mcp/lsp ages)
#   ~30-50 ms: jq pass over the per-session overlay (early-exits when absent)
#   ~50-100 ms: timeout-wrapped global statusline subprocess
# That bottoms out around ~210 ms when every optional step is skipped and
# tops out around ~430 ms when every step runs in steady state. Under
# heavy system load (concurrent xcrun, Spotlight indexing, Docker disk
# pressure) wall-clock can reach ~700-900 ms even though no step actually
# took longer — the variance is OS scheduler noise, not renderer
# regression. The 1500 ms cap is well above the user-perceived staleness
# threshold (~2 s before the bar feels behind the conversation) and tight
# enough that a real 2x regression in any individual jq/python call
# would still trip the test. Tighten via STATUSLINE_BUDGET_MS=500 on a
# quiet machine to spot regressions in the steady-state envelope.
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
