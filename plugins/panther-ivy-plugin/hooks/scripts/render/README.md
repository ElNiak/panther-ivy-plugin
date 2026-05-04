# render/

Hooks that render Ivy tool results, project state, workflow-aware annotations, and session summaries.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `tool-result.py` | PostToolUse | `ivy_*` | Format MCP-tool output as user-facing prose / tables. |
| `project-md.py` | PostToolUse | `mcp__.*ivy_workflow_state` | Regenerate `protocol-testing/<protocol>/PROJECT.md` rolled-up view. |
| `workflow-aware-annotation.py` | PostToolUse | `Write\|Edit\|Agent` | Surface workflow-aware annotation + statusline overlay write. |
| `summary.py` | Stop | (none) | Render the per-session activity summary (split into a package by PR4). |

See `.claude/rules/output-style.md` for the systemMessage prefix conventions.
