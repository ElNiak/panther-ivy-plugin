# shellcheck shell=bash
# Test-file segment: test:<basename>, truncated to 20 chars with `…`.
# Reads STC_TESTFILE populated by statusline_cache_load().

_STATUSLINE_TESTFILE_MAXLEN=20

render_testfile() {
    local basename="${STC_TESTFILE:-}"
    [ -n "$basename" ] || return 0

    if [ "${#basename}" -gt "$_STATUSLINE_TESTFILE_MAXLEN" ]; then
        local keep=$((_STATUSLINE_TESTFILE_MAXLEN - 1))
        basename="${basename:0:keep}…"
    fi
    printf 'test:%s' "$basename"
}
