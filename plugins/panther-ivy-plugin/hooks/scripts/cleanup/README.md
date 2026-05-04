# cleanup/

Hooks that perform startup and shutdown cleanup tasks.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `stale-pids.py` | SessionStart | (none) | Reap stale PID files from prior sessions. |
| `stale-workflow.py` | SessionStart | (none) | Detect and clear stale active-workflow YAML (>2h old). |
| `ivy-lsp.py` | SessionEnd | (none) | Tear down the ivy-lsp sidecar at session end. |

See `.claude/rules/journaling-contract.md` §11 for the session-activity flag conventions.
