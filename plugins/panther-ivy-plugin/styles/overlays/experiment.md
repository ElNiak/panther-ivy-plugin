# Experiment Mode -- Style Overlay

## Dimension Overrides
- **Verbosity**: Diagnostic. Lead with the IUT verdict, then trace observations.
- **Tone**: Forensic. Cite pcap line numbers, log timestamps, RFC sections.
- **Structure**: Per-IUT-run sections; numbered observations within each.

## Mandatory Sections
- **IUT verdict** -- `NO_VIOLATION_FOUND` / `NON_COMPLIANT` / `TESTER_CRASH` / `IUT_CRASH` per the experiment's `test-results.yaml`.
- **9-step trace analysis** -- per the canonical recipe: (1) `test-results.yaml` verdict, (2) Ivy log assertion failures, (3) tester stderr, (4) IUT stderr, (5) message-type pcap distribution, (6) compare to expected wire trace, (7) cross-check Ivy log events vs pcap, (8) re-grade against RFC normative text, (9) capture finding via `ivy_workflow_state(append_journal, error)` if NON_COMPLIANT.
- **Gate verdict** -- present when a G5 gate has fired this turn; see `tool-renderers/ivy_verdict.md`.
- **Next Steps** -- scoped to experiment actions: re-run with different config, escalate to refine for spec-bug, escalate to review for coverage-gap.

## Tool Presentation
- `panther run`: progress + verdict line (suppress raw container logs).
- `ivy_iut_test`: structured per the post-experiment 9-step recipe.
- pcap analysis: tabulate by message type with counts.

## Phase Modifiers

### setup
- Show experiment-config target and IUT name.
- Confirm container build status.

### run
- Stream `panther run` progress; suppress raw container logs.
- On verdict: emit single-line summary.

### analyze
- Override verbosity to detailed; explain root cause hypothesis.
- Include pcap line excerpts (3-5 lines around the deviation).
- Cite the RFC section the deviation maps to.

### handoff
- On `spec-bug`: emit `pending_dispatch` to refine.
- On `coverage-gap`: emit `pending_dispatch` to review.
- On `NO_VIOLATION_FOUND`: workflow complete; emit terminal-state line.
