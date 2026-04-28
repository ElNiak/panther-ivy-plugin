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
| `[IVY-LINT]` | PostToolUse | `post-write-ivy-lint.sh` | Structural issues found in a written `.ivy` file (missing header, unbalanced braces). |
| `[G2 modeling gate]` | PostToolUse | `assess-modeling.py` | Ivy layer file written during `build` workflow; G2 adversarial modeling critic dispatched. |
| `[G3 test-spec gate]` | PostToolUse | `assess-testspec.py` | Ivy test-spec file written during `build` workflow; G3 adversarial test-spec critic dispatched. |
| `[G4 verification gate]` | PostToolUse | `record-workflow-error.py` | `ivy_verify` completed; G4 verification critic dispatched. |
| `[G5 trace-analysis gate]` | PostToolUse | `assess-trace.py` | `ivy_iut_test` completed; G5 trace-analysis critic dispatched. |

## systemMessage + additionalContext convention (Phase D)

Phase D standardised the hook output format on a twin-key emission: hooks emit `systemMessage` for content the user must see (denial reasons, MCP disconnect warnings, gate dispatches) and `additionalContext` for content that should enter the agent's context as background information (workspace prefixes, indexing status, marker rows like the ones tabulated above). The split exists because some hook output benefits from explicit user visibility while other output is only useful as silent agent context, and forcing one channel to carry both produced noisy system reminders pre-Phase-D. Both keys are written via the shared helper in `hooks/scripts/hook_utils.py` so every PostToolUse, SessionStart, and Notification hook converges on the same envelope. When triaging unexpected hook behaviour, check that the relevant script populates the correct key for the audience: user-actionable signals belong in `systemMessage`, contextual prefixes in `additionalContext`.
