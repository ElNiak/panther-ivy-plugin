# lib/

Shared Python utility packages — **not user-facing hooks**. Hook scripts
in sibling folders import these via `from lib.X import Y`. `hooks.json`
invokes hook entry-points only, never `lib/`.

| Path | Purpose |
|---|---|
| `lib/hook_utils/` | `emit_hook_output`, `emit_noop`, workspace detection, session-id resolution, MCP health state, `push_warning` / `drain_warnings` buffer. |
| `lib/workflow_state/` | Read/write wrappers for `.panther-ivy/active-workflow` and `scaffold-state.yaml`. |
| `lib/statusline_cache/` | Populates `~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json` consumed by the bash renderer at `scripts/statusline/main.sh`. |
| `lib/style_utils.py` | Style-composition helpers for the `render/` hooks. |
| `lib/log_event.py` | Low-level JSONL event writer shared by `observability/observe.py` and other consumers. |
| `lib/ivy_path.py` | Path helpers for `.ivy` file resolution under `protocol-testing/`. |

A rename within `lib/` always requires a tree-wide grep across the
`hooks/scripts/` and `tests/` trees because the importers reach this
package via `from lib.X import Y` rather than through `hooks.json`.
