---
paths: ["**/skills/*/SKILL.md"]
---

# Output Style

Each workflow skill's output formatting is managed by the plugin style system.
Follow the style directives injected via `additionalContext`; they carry the
active workflow overlay and phase modifier. Tool results that arrive
pre-formatted in `hookSpecificOutput` are already in their final form — read
them as-is and pass them through to the user unchanged.

## Context injectors

These hooks inject identifiable `additionalContext` messages into the agent's context. Recognise the prefix to know which hook produced it and at what event.

| Prefix / Marker | Event | Source hook | Meaning |
|---|---|---|---|
| `[ivy-workspace]` | SessionStart | `detect-ivy-workspace.sh` | Ivy/PANTHER project detected; workspace root and MCP status exported. |
| `[ivy-indexing]` | SessionStart | `wait-for-indexing.sh` | MCP server readiness status after session startup. |
| `[ivy-indexing]` | PreToolUse | `check-indexing-ready.sh` | LSP still indexing; tool call may be denied or warned. |
| `[ivy-startup]` | PreToolUse | `check-indexing-ready.sh` | MCP server still initialising; tool call denied until ready. |
| `[ivy-health]` | PreToolUse | `check-indexing-ready.sh` | MCP may not be fully started; tool call allowed with advisory. |
| `[ivy-health]` | Notification | `notify-mcp-disconnect.py` | Ivy MCP server disconnected; run `/mcp` to reconnect. |
| `[ROUTING:AVAILABLE]` | UserPromptSubmit | `route-user-prompt.py` | Ivy workspace detected with no active workflow; lists available workflow skills. |
| `[ROUTING:CONTINUE]` | UserPromptSubmit | `route-user-prompt.py` | Active workflow matches prompt intent; agent should stay in current workflow. |
| `[ROUTING]` | UserPromptSubmit | `route-user-prompt.py` | A workflow skill matches the prompt; agent should activate it. |
| `(style overlay)` | UserPromptSubmit | `compose-style.py` | Active workflow's output-style overlay injected for this turn; no fixed prefix. |
| `[IVY-LINT]` | PostToolUse | `post-write-ivy-lint.sh` | Structural issues found in a written `.ivy` file (missing header, unbalanced braces). |
| `[INTERACTION CHECKPOINT]` | PostToolUse | `interaction-checkpoint.py` | `ivy_verify` failure or coverage gap detected; user discussion required before proceeding. |
| `[G2 modeling gate]` | PostToolUse | `assess-modeling.py` | Ivy layer file written during `build` workflow; G2 adversarial modeling critic dispatched. |
| `[G3 test-spec gate]` | PostToolUse | `assess-testspec.py` | Ivy test-spec file written during `build` workflow; G3 adversarial test-spec critic dispatched. |
| `[G5 trace-analysis gate]` | PostToolUse | `assess-trace.py` | `ivy_iut_test` completed; G5 trace-analysis critic dispatched. |
