---
description: Calibrated semantics of the three gate-verdict outputs (SOUND, UNSOUND, ABSTAIN) used by every adversarial gate (G0-G8). ABSTAIN is a first-class verdict, not a synonym for SOUND or WARN. Workflow skills cite this rule rather than paraphrasing the semantics in their bodies.
paths: ["**/skills/*/SKILL.md"]
---

<purpose>
Three calibrated verdict outputs cited by every adversarial-gate dispatch.
The text below is the canonical semantics; the workflow skills reference it
rather than restating verdict meanings in their Red Flags or narrative
sections. Workflow-specific routing on each verdict (which phase to enter,
which dispatch to emit) stays in the owning ops skill.
</purpose>

<context>
The plugin runs adversarial quality gates G0-G8 across plan-mode (G0),
plan-fidelity (G0b), exploration (G1), modeling (G2), test-spec (G3),
verification (G4), trace-analysis (G5), knowledge-capture (G6),
triage-diagnosis (G7), and triage-repair-verify (G8). Every gate dispatch
returns one of three verdicts. The verdict severity system is documented
in `.claude/rules/ivy-formatting.md` §"Severity Systems"; this rule
expands the calibrated meaning of each verdict and the cross-rule
constraints that bind it.

Rule loaded via `paths: ["**/skills/*/SKILL.md"]` so any skill activation
brings the calibrated semantics into context. The rule is referenced (not
duplicated) by scaffold-ops, refine-ops, experiment-ops, review-ops,
triage-ops, and meta-self-mod-ops. Glossary content for `SOUND` and
`ABSTAIN` is defined in `skills/refine-ops/references/glossary.md` and
promoted here because the same calibrated semantics apply across all six
ops skills, not just refine.
</context>

## Three verdict states

| Verdict | Meaning |
|---|---|
| **SOUND** | Tool result and critic vote agree the property holds. The workflow may proceed past the gate. SOUND is necessary but not sufficient — see `iron-laws.md` for the cross-rule constraints (e.g., `NO_FIX_WITHOUT_VERIFY` requires fresh evidence beyond a SOUND verdict; a SOUND `ivy_verify` may still be invalidated by `STALENESS_RULE` if the include closure changed). |
| **UNSOUND(#NN, reason, file:line)** | Critics identified a violation against catalog pattern `#NN`. Callers MUST resolve the cited `[GAP: #NN]` markers — fix-and-re-verify, or DEFERRED-promote with `// DEFERRED YYYY-MM-DD: <reason>` — before progression. UNSOUND blocks the gate; it does not authorise a skip. Marker emission and resolution lifecycle: `.claude/rules/gap-markers.md`. |
| **ABSTAIN(abstain_reason)** | First-class output signalling insufficient evidence. NOT a synonym for SOUND, WARN, UNSURE, or "proceed cautiously". Callers proceed to their workflow's diagnose phase using `abstain_reason` as the starting hypothesis — they do NOT treat the upstream tool result as authoritative. |

## Workflow-specific ABSTAIN routing

ABSTAIN's calibrated meaning is universal; the routing target is
workflow-specific and stays in the owning skill body:

- `scaffold-ops`: ABSTAIN on G1 → resolve the evidence gap or escalate to
  Opus tier; do not enter Phase 3 on ABSTAIN.
- `refine-ops`: ABSTAIN on G4 → Phase 6 Diagnose using `abstain_reason`
  as the starting hypothesis; the upstream `ivy_verify` is not authoritative.
- `experiment-ops`: ABSTAIN on G5 → return verdict with caveat naming the
  unverifiable trace dimension; surface the abstain_reason to the user.
- `review-ops`: ABSTAIN on G5 → append `gate_verdict{verdict: "abstain",
  abstain_reason: ...}` and ask the user whether to re-run via
  `pending_dispatch(experiment, phase_hint="iut")` or accept inconclusive.
- `triage-ops`: ABSTAIN on G7 (post-Phase-2, pre-fix) → halt; do NOT
  present the rejected diagnosis to the user; loop back to "Identify
  failures" and re-diagnose with the critic's `CITATION_FAIL` evidence
  as the new starting hypothesis. ABSTAIN on G8 (post-Phase-3,
  pre-return) → return to caller with caveat in digest naming the
  unverifiable post-fix indicator.
- `meta-self-mod-ops`: ABSTAIN on either reviewer in the three-loop →
  retry the implementer with the cited issues, then re-run the failing
  reviewer.

## Cross-rule constraints

- `iron-laws.md` — `NO_FIX_WITHOUT_VERIFY` binds: a SOUND verdict alone
  does not license a fix-resolution claim; a fresh `ivy_verify` /
  `ivy_compile` result on the edited spec must follow the fix.
  `STALENESS_RULE` binds: a SOUND tool-result is stale if any file in the
  include closure changed since the result's timestamp.
- `gap-markers.md` — UNSOUND verdicts emit `[GAP: #NN]` markers; the
  resolution loop (fix or DEFERRED-promote) is documented there.
- `agent-dispatch.md` — gate dispatches use the asymmetric Sonnet × 5
  vote; on critic dispatch failure (timeout, context exhaustion, partial
  output), the rule's failure-recovery contract applies. Auto-retry
  budgets: Sonnet 90 s, Opus 180 s.
- `ivy-formatting.md` §"Severity Systems" — gate verdicts are one of
  three orthogonal severity systems. SOUND/UNSOUND/ABSTAIN does not map
  to PASS/FAIL/WARN (tool-outcome system) or ERROR/WARNING/INFO
  (finding-severity system). An UNSOUND gate verdict may cite multiple
  ERROR-severity findings; an ABSTAIN is not a WARN.
- `journaling-contract.md` §3 — `gate_verdict` is a closed-list journal
  event type with required fields `gate`, `verdict`, `vote` and optional
  fields `patterns`, `cycle`, `tier`, `duration_s`, `abstain_reason`.
  The orchestrator writes one `gate_verdict` after aggregating the 3
  critic returns; critics themselves do NOT write the journal (per
  contract §1).

## Anti-paraphrase rule

Skills referencing this rule MUST NOT paraphrase the verdict meanings in
their Red Flags tables or narrative bodies. Concrete patterns to avoid:

- "ABSTAIN means proceed cautiously" — wrong; ABSTAIN means insufficient
  evidence, not a soft pass.
- "SOUND means done" — wrong; SOUND is necessary, not sufficient (see
  STALENESS_RULE, NO_FIX_WITHOUT_VERIFY).
- "UNSOUND can be ignored if minor" — wrong; UNSOUND blocks the gate
  until markers are resolved or DEFERRED-promoted.

Workflow-specific routing on each verdict is allowed and lives in the
owning ops skill (per the Workflow-specific ABSTAIN routing table above).

<integration
  cited-by="skills/scaffold-ops, skills/refine-ops, skills/experiment-ops, skills/review-ops, skills/triage-ops, skills/meta-self-mod-ops"
  related-rules=".claude/rules/iron-laws.md, .claude/rules/gap-markers.md, .claude/rules/agent-dispatch.md, .claude/rules/ivy-formatting.md, .claude/rules/journaling-contract.md"
  glossary-source-superseded="skills/refine-ops/references/glossary.md (gate-verdict subset only; MPE / iron law / pending_dispatch entries remain in the glossary)"/>
