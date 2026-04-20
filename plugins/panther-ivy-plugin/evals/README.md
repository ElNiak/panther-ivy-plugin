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
