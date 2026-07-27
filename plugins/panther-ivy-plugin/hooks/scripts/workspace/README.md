# workspace/

Hooks that detect, scope, and notify changes to the active Ivy workspace.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `detect.py` | SessionStart | (none) | Detect standalone vs. submodule project layout; write `IVY_WORKSPACE_ROOT` env file and seed the statusline cache. |
| `scope.py` | PreToolUse | `Write\|Edit` | Block edits outside the active workspace's `protocol-testing/<name>/` tree. |
| `change-notify.py` | PostToolUse | `mcp__plugin_panther-ivy.*_workspace` | Surface a status-line banner when `ivy_workspace(action="set"\|"clear")` fires. |

No dedicated rule; see `skills/ivy/SKILL.md` for workspace context.
