# shellcheck shell=bash
# Test-file segment: test:<basename>, truncated to 20 chars with `…`.
#
# Prefers STC_SESSION_TEST_FILE (per-session overlay populated by
# statusline_overlay_load) so two Claude Code windows in the same
# workspace+protocol see their OWN last-edited file, not whichever
# wrote most recently. Falls back to STC_TESTFILE (workspace-shared
# cache populated by statusline_cache_load) when no overlay exists —
# preserves behavior for sessions whose hook payload omits session_id
# (offline / smoke-test paths).

_STATUSLINE_TESTFILE_MAXLEN=20

render_testfile() {
    local basename="${STC_SESSION_TEST_FILE:-}"
    [ -n "$basename" ] || basename="${STC_TESTFILE:-}"
    [ -n "$basename" ] || return 0

    if [ "${#basename}" -gt "$_STATUSLINE_TESTFILE_MAXLEN" ]; then
        local keep=$((_STATUSLINE_TESTFILE_MAXLEN - 1))
        basename="${basename:0:keep}…"
    fi
    printf 'test:%s' "$basename"
}
