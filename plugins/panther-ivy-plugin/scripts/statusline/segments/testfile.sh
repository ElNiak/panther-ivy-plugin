# shellcheck shell=bash
# Test-file segment: test:<basename>, truncated to 20 chars with `…`.
# Returns nothing (hides the segment) when the cache has no test_file basename.

_STATUSLINE_TESTFILE_MAXLEN=20

render_testfile() {
    local cache_file="$1"
    local basename
    basename="$(statusline_cache_get "$cache_file" '.test_file.basename')" || return 0
    [ "$basename" = "null" ] && return 0

    if [ "${#basename}" -gt "$_STATUSLINE_TESTFILE_MAXLEN" ]; then
        local keep=$((_STATUSLINE_TESTFILE_MAXLEN - 1))
        basename="${basename:0:keep}…"
    fi
    printf 'test:%s' "$basename"
}
