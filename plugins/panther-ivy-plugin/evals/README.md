# Trigger Evals

Per-gate trigger evaluations for the adversarial quality gates (G1–G5). Each `g{N}_trigger_eval.json` contains 20 entries (10 should-trigger + 10 should-not). Used as a manual harness to keep gate-dispatch quality measurable.

## How to run

For each entry in a `g{N}_trigger_eval.json`:

1. Open a fresh Claude Code session in this plugin's workspace.
2. Send the entry's `prompt` verbatim as the first user message.
3. Observe whether the gate fires:
   - **Should-trigger entries:** the gate's PostToolUse / UserPromptSubmit hook should emit a dispatch directive (look for `[G{N} ...]` in `additionalContext`) within the first turn, and Claude should respond by loading `reflection-patterns` and dispatching critics.
   - **Should-not-trigger entries:** the gate must remain silent — no dispatch directive, no critic spawn, no `gate_verdict` event written for this gate.
4. Record the outcome alongside the `expected_phase` field.

## Pass criterion

Each gate's eval must hit ≥ 18 / 20 expected outcomes to be considered well-tuned. Failures below this bar indicate either the dispatch hook is too eager (false positives) or too narrow (false negatives) and the trigger conditions need adjustment.

## When to update

When a gate's hook trigger logic changes (file-pattern matcher, workflow-active check, methodology overlay logic), re-run the eval. When a new failure mode is added to the catalog and surfaces in real use, add a should-trigger entry that exercises it.

## Schema variants

Most trigger evals use `expected_phase` (per-phase gates: G1, G2, G3, G4, G5). G0b is per-action — it fires on every PostToolUse-eligible action while a plan_approved is unpaired in the journal — so its eval uses **`expected_state`** keyed to journal predicates (`"plan_approved_unpaired"` for the trigger condition; `null` for the negative case). G6's eval uses `expected_state: "session_end_unpaired"` for the same reason.

Implementations of the eval runner that read these files must accept either `expected_phase` (string keyed to a workflow phase) or `expected_state` (string keyed to a journal predicate); per-prompt entries carry exactly one of the two fields plus the prompt.
