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
| `[ivy-journal]` | SubagentStart | `inject-journaling-contract.py` | Journaling-contract directive injected for a dispatched plugin specialist (full directive) or a critic (5-line stub). The full contract is loaded by the agent's mandatory first-action `Read .claude/rules/journaling-contract.md`. |
| `[ivy-journal]` | (skill-internal) | ops-skill terminal-state per `journaling-contract.md` §8 | Per-workflow user-visible terminal-state line in the format `[ivy-{workflow}] {phase} {verdict}. {next_action_phrase}` (e.g. `[ivy-verify] Phase 4 PASS (G4 SOUND, vote 2-of-3). Dispatching review for coverage follow-up.`). Emitted by scaffold-ops, verify-ops, review-ops, triage-ops, meta-self-mod-ops at end-of-turn before clearing active-workflow. |
| `[ivy-resume]` | (orchestrator-internal) | `skills/ivy/SKILL.md` Phase 1.5 | Orchestrator consumed a fresh `pending_dispatch` and is warm-resuming a workflow. Format: `[ivy-resume] resuming <workflow> (<phase>) from <source_workflow>'s pending_dispatch`. |

## systemMessage + additionalContext convention (Phase D)

Phase D standardised the hook output format on a twin-key emission: hooks emit `systemMessage` for content the user must see (denial reasons, MCP disconnect warnings, gate dispatches) and `additionalContext` for content that should enter the agent's context as background information (workspace prefixes, indexing status, marker rows like the ones tabulated above). The split exists because some hook output benefits from explicit user visibility while other output is only useful as silent agent context, and forcing one channel to carry both produced noisy system reminders pre-Phase-D. Both keys are written via the shared helper in `hooks/scripts/hook_utils.py` so every PostToolUse, SessionStart, and Notification hook converges on the same envelope. When triaging unexpected hook behaviour, check that the relevant script populates the correct key for the audience: user-actionable signals belong in `systemMessage`, contextual prefixes in `additionalContext`.
