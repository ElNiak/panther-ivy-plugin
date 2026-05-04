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
| `[ivy-workspace]` | SessionStart | `workspace/detect.py` | Ivy/PANTHER project detected; workspace root and MCP status exported. |
| `[ivy-indexing]` | SessionStart | `mcp/indexing-wait.py` | MCP server readiness status after session startup. |
| `[ivy-indexing]` | PreToolUse | `mcp/indexing-ready.py` | LSP still indexing; tool call may be denied or warned. |
| `[ivy-startup]` | PreToolUse | `mcp/indexing-ready.py` | MCP server still initialising; tool call denied until ready. |
| `[ivy-health]` | PreToolUse | `mcp/indexing-ready.py` | MCP may not be fully started; tool call allowed with advisory. |
| `[ivy-health]` | Notification | `mcp/disconnect-notify.py` | Ivy MCP server disconnected; run `/mcp` to reconnect. |
| `[IVY-LINT]` | PostToolUse | `posttooluse/lint/ivy.py` | Structural issues found in a written `.ivy` file (missing header, unbalanced braces). |
| `[ivy-block]` | PreToolUse | `pretooluse/block-direct-ivy.py` | Bash command invoked `ivyc` / `ivy_check` / `ivy_show` / `ivy_to_cpp` directly; advisory MCP-tool suggestion table surfaced (always exit 0). |
| `[ivy-skill]` | PostToolUse | `record/skill-invocation.py` | `Skill` tool fired; for plugin skills (`panther-ivy-plugin:*`) auto-loads `references/*.md` into `additionalContext` (capped at 8000 chars; degrades to a file listing on overflow). Non-plugin skills get the status line only. |
| `[ivy-noop]` | (any event) | any hook | Hook ran but took no action. Emitted via `hook_utils.emit_noop` so the user can visually filter no-op lines from action-bearing ones. |
| `[G2 modeling gate]` | PostToolUse | `posttooluse/gates/run-gate.py --id g2` (logic in `posttooluse/gates/gate_handlers.py::dispatch_g2`) | Ivy layer file written during `scaffold` workflow; G2 adversarial modeling critic dispatched. |
| `[G3 test-spec gate]` | PostToolUse | `posttooluse/gates/run-gate.py --id g3` (logic in `posttooluse/gates/gate_handlers.py::dispatch_g3`) | Ivy test-spec file written during `scaffold` workflow; G3 adversarial test-spec critic dispatched. |
| `[G4 verification gate]` | PostToolUse | `record/workflow-error.py` | `ivy_verify` completed; G4 verification critic dispatched. |
| `[G5 trace-analysis gate]` | PostToolUse | `posttooluse/gates/run-gate.py --id g5` (logic in `posttooluse/gates/gate_handlers.py::dispatch_g5`) | `ivy_iut_test` completed; G5 trace-analysis critic dispatched. |
| `[ivy-journal]` | SubagentStart | `journaling/contract-inject.py` | Journaling-contract directive injected for a dispatched plugin specialist (full directive) or a critic (5-line stub). The full contract is loaded by the agent's mandatory first-action `Read .claude/rules/journaling-contract.md`. |
| `[ivy-journal]` | (skill-internal) | ops-skill terminal-state per `journaling-contract.md` §8 | Per-workflow user-visible terminal-state line in the format `[ivy-{workflow}] {phase} {verdict}. {next_action_phrase}` (e.g. `[ivy-refine] Phase 4 PASS (G4 SOUND, vote 2-of-3). Dispatching review for coverage follow-up.`). Emitted by scaffold-ops, refine-ops, experiment-ops, review-ops, triage-ops, meta-self-mod-ops at end-of-turn before clearing active-workflow. |
| `[ivy-resume]` | (orchestrator-internal) | `skills/ivy/SKILL.md` Phase 1.5 | Orchestrator consumed a fresh `pending_dispatch` and is warm-resuming a workflow. Format: `[ivy-resume] resuming <workflow> (<phase>) from <source_workflow>'s pending_dispatch`. |

## systemMessage + additionalContext convention (Phase D)

Phase D standardised the hook output format on a twin-key emission: hooks emit `systemMessage` for content the user must see (denial reasons, MCP disconnect warnings, gate dispatches) and `additionalContext` for content that should enter the agent's context as background information (workspace prefixes, indexing status, marker rows like the ones tabulated above). The split exists because some hook output benefits from explicit user visibility while other output is only useful as silent agent context, and forcing one channel to carry both produced noisy system reminders pre-Phase-D. Both keys are written via the shared helper in `hooks/scripts/hook_utils.py` so every PostToolUse, SessionStart, and Notification hook converges on the same envelope. When triaging unexpected hook behaviour, check that the relevant script populates the correct key for the audience: user-actionable signals belong in `systemMessage`, contextual prefixes in `additionalContext`.

## State-persistence message templates (T1 / T2 / T3)

Hooks that persist state to disk (`.panther-ivy/workflow-journal.yaml`, `.panther-ivy/*.jsonl`, env files, session-id files) or to the statusline cache compose their `systemMessage` from one of three canonical templates. The split exists so users skimming a session log can instantly tell whether a hook recorded user-replayable data they may want to audit (T1), appended to the workflow journal (T2), or reported a state transition (T3) — and in the first two cases, find the file to inspect.

```
T1. recorded     [ivy-<surface>] recorded <count> <thing>(s) to <path> [(id=<short>)]
T2. journal      [ivy-<surface>] <event> appended to journal at <path> [(entry=#NN)]
T3. state-change [ivy-<surface>] <thing>: <new> (was: <prev>)
```

When to use which:

- **T1 (recorded)** — Hook persists user-replayable data the user might want to audit later (JSONL records, session-end summaries). Always cite the file path; cite `id` if the record has one. Example: `[ivy-question] recorded 1 question(s), 1 answer(s) to .panther-ivy/askuserquestion-log.jsonl (id=7912511b967f)`.
- **T2 (journal)** — Hook appends an event to the workflow journal at `.panther-ivy/workflow-journal.yaml`. Always cite the journal path; cite `entry=#NN` when the writer can compute it cheaply. Example: `[ivy-gate] G2 modeling-gate dispatched appended to journal at .panther-ivy/workflow-journal.yaml (entry=#42)`.
- **T3 (state-change)** — Hook reports a transition the user cares about (workspace change, status change). The banner *is* the user-visible state; no path citation needed because the banner replaces it. Example: `[ivy-workspace] active workspace: bgp (was: quic)`. Render `(none)` for empty values on either side so set/clear render symmetrically.

The `<surface>` slot follows the existing `[ivy-<surface>]` prefix table above. New surfaces should be added to that table when introduced.

These templates are enforced by `tests/test_observability_write_discipline.py` — an AST + regex scan that flags hook scripts containing a write marker (`write_text`, `Path.open(... 'w'/'a' ...)`, `json.dump`, `yaml.dump`, `append_journal_event`, `statusline_cache.update_from_hook`) but emitting no `systemMessage` matching T1/T2/T3. Two scripts (`observability/observe.py`, `observability/log_event.py`) are exempt because they fire on every event and would flood the scrollback if they cited paths.
