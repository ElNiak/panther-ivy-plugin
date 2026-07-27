# statusline/

Hooks that synchronize the per-session statusline cache.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `sync.py` | SessionStart, PostToolUse | `mcp__.*ivy_workflow_state` | Sync workspace + workflow state into the statusline cache. |

Companion library at `hooks/scripts/lib/statusline_cache/`.
