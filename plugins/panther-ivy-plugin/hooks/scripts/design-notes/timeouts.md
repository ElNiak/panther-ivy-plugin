# Hook timeouts

Rationale for non-default timeout values configured in `hooks/hooks.json`.

## render-tool-result.py: 10s (bumped from 5s, 2026-04-23)

On slow filesystems (NFS, encrypted volumes, containers with bind mounts), the
combined cost of `find_protocol_dir()` directory walk + YAML parse of the
active-workflow file + style composition has been observed to exceed 5 seconds.
The 10 second budget provides ~2x headroom without meaningfully delaying
user-visible responses on fast disks.

The hook is PostToolUse-scoped on a small allowlist (`ivy_verify`,
`ivy_coverage`, `ivy_diagnostics`, `ivy_compile`, `ivy_quality`), so it does
not fire on every edit — the higher timeout is acceptable in that context.

If this becomes the common path rather than an edge case, consider memoizing
`find_protocol_dir()` (e.g. via `functools.lru_cache` at module scope). Hooks
are short-lived subprocesses, so the per-invocation win is modest, but five
different hook scripts now call `WorkflowContext.current()` which in turn
calls `find_protocol_dir()` unconditionally — the directory walk repeats
across scripts but not within a single invocation.
