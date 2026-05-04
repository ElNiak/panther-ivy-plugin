# mcp/

Hooks that monitor MCP-tool health, retry transient failures, and surface MCP state to the user.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `health.py` | PreToolUse | `mcp__.*ivy` | Circuit breaker for the panther-ivy-plugin MCP server. |
| `activity.py` | PostToolUse | `mcp__plugin_panther-ivy.*` | Mark per-session activity flag for any panther-ivy MCP tool call. |
| `retry.py` | PostToolUseFailure | (none) | Auto-retry read-only MCP tools once on failure. |
| `disconnect-notify.py` | Notification | (none) | Surface a status line when the MCP server disconnects. |
| `indexing-ready.py` | PreToolUse | `mcp__.*ivy` | Gate MCP tool calls until the LSP indexer is ready. |
| `indexing-wait.py` | SessionStart | (none) | Wait for the LSP indexer to finish initial scan. |

See `.claude/rules/mcp-tool-reliability.md` for the canonical recovery pattern.
