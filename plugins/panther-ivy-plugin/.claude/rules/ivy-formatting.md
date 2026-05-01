---
description: "RFC citation format ([rfcNNNN:X.Y]), error/warning formatting, the three orthogonal severity systems (Tool-outcome PASS/FAIL/WARN, Gate-verdict SOUND/UNSOUND/ABSTAIN, Finding ERROR/WARNING/INFO), and the Considerations self-review block."
# Loaded on demand by name from output styles, workflow skills, and agents; not auto-injected on file edits.
---

## Ivy Formatting Conventions

- Cite RFC sections as `[rfcNNNN:X.Y]` inline, never as footnotes. Always include
  the complete normative quote from the cited section (all MUST/SHOULD/MAY language).
  Never truncate or paraphrase normative text.
- Format errors as: `ERROR: {file}:{line} -- {message}`.
- Format warnings as: `WARN: {file}:{line} -- {message}`.
- Reference Ivy files with relative paths from protocol-testing root.
- When referencing claims, assertions, or design decisions, quote the source
  verbatim with a bracketed reference.
- Suppress raw JSON from MCP tool results. Render as formatted prose or tables.

## Self-Review

- Append a "Considerations" block to every response that contains any one
  of: analysis, recommendations, or design choices for the workflow tasks. Treat this trigger as
  disjunctive — a response with a single recommendation still qualifies.
  The block lists:
  - **Pro**: What this approach gets right
  - **Con**: What risks, trade-offs, or limitations exist
  - **Alternatives considered**: Other options and why they were not chosen
- This rule governs Claude's response to the user, not plugin source documents
  (skills, rules, agents) that teach these conventions.
- For simple factual outputs (tool results, file listings), skip self-review.

## Severity Systems

Three orthogonal severity systems exist in the plugin. Use the system that
matches the concept being labeled.

1. **Tool-outcome**: PASS / FAIL / WARN.
   Use for the result of a mechanical tool run (`ivy_verify` returning
   success/failure, a health-check step, a compile result). PASS/FAIL are
   binary outcomes; WARN signals a tool succeeded but produced advisory
   output. Used by: triage Phase 1-3, the `/nct-health` runbook, verify
   Phase 3 compile result, `/nct-check` output.

2. **Gate verdict**: SOUND / UNSOUND(#NN, reason, file:line) / ABSTAIN.
   Use for the calibrated verdict of an adversarial quality gate (G0-G8).
   ABSTAIN is a first-class output signalling insufficient evidence, not a
   synonym for WARN or UNSURE. Used by: the three gate critics
   (`g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`); the
   inline G2/G3/G4/G5/G7/G8 dispatches in the build / verify / review /
   triage ops-skills; `gate_verdict` journal entries.

3. **Finding severity**: ERROR / WARNING / INFO.
   Use for the severity of a code-level or workflow-level finding that has
   a file:line locator. Format per the existing canonical rule above
   (`ERROR: {file}:{line} -- {message}`). Used by: `ivy-reviewer-agent`
   interactive coverage / quality output, build Phase 5 findings, review
   Phase 3 findings, `ivy-verifier-agent` diagnostic reports.

These systems do not map onto each other. A FAIL tool-outcome may correspond
to multiple ERROR findings; an UNSOUND gate verdict may cite one or more
ERROR-severity patterns; and an ABSTAIN is not a WARN.

The audit-report-specific taxonomy `Critical / Major / Minor / Nit` used in
the 2026-04-23 workflow audit belongs to that audit report, not to the
runtime plugin, and is not one of the systems above.
