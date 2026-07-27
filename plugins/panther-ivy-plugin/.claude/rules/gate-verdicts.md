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

### G0 — plan-soundness (per-plan)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Approved plan is internally consistent (no contradictory assumptions, all referenced files exist, ordering avoids broken intermediate states). | Emit `pending_dispatch(<caller>, reason="post-G0-SOUND")` and proceed to first task. |
| UNSOUND(#NN, reason, plan-section) | Soundness gap: a missing prerequisite, false assumption, unverifiable claim, or ordering error. | **Halt plan execution.** Surface the gap to user with direct plan quotes; require revision via plan-mode re-entry. |
| ABSTAIN | Critics had insufficient evidence (mixed votes, unreadable plan file, dependency files inaccessible). | Re-dispatch `g-plan-critic` ×3 with refined input. After 2 ABSTAIN cycles, halt and surface. |

### G0b — plan-fidelity (per-action)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Action conforms to first task of approved plan. | Emit `pending_dispatch(<caller>, reason="post-G0b-SOUND")` and proceed. Subsequent actions in the same plan task do not re-fire G0b — only the *first* action after `plan_approved` triggers it. |
| UNSOUND(#NN, drift, plan-task) | Action drifted from the plan's first task. The drift cite is mandatory: file path, planned vs observed, and the plan task that was violated. | **Halt next actions.** Surface drift to user with direct code+plan quotes, citing the violated `plan-task`. User options (the only three): (a) **revert** — `git restore <file>` to undo the action, then resume from plan-mode; (b) **override** — append `decision{kind=g0b_override, rationale=<text>}` and continue without the gate (audit trail preserved); (c) **return to plan-mode** — keep the action's filesystem effect, but force a fresh plan that incorporates the drift. |
| ABSTAIN | Critics had insufficient evidence (mixed votes, missing CITATION_PASS spot-checks, unreadable file state). | Re-dispatch `g-fidelity-critic` ×3 with the original prompt PLUS a `tool_input_digest` and the `plan-task` reference. After 2 ABSTAIN cycles in a row, halt and surface the same drift-options prompt as UNSOUND, with `<drift>` set to "abstain after 2 cycles". |

### G2 — modeling (per-layer)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Layer file conforms to verification-failures catalog ranges #200-249 + #250-299 (+ #260-289 if NSCT). | Append `gate_verdict{gate=g2, verdict=SOUND}`; proceed to next layer. |
| UNSOUND(#NN, reason, file:line) | Catalog violation found in the layer file. | Write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only — never let a critic edit the file). Do not proceed to the next layer until each `[GAP:]` is resolved or promoted to `// DEFERRED YYYY-MM-DD: ...`. |
| ABSTAIN | Critics could not establish soundness with available evidence. | Re-dispatch with refined input; cap at 2 cycles → halt and surface to user. |

### G3 — test-spec (per-test-spec)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Test spec conforms to catalog ranges #200-208 + #256-259 + #300-399; coverage matrix matches RFC requirement manifest. | Append `gate_verdict{gate=g3, verdict=SOUND}`; proceed to `ivy_compile` / `ivy_verify`. |
| UNSOUND(#NN, reason, file:line) | Test spec gap (typically: silently fails to cover a MUST requirement, or over-constrains the generator). | Write `[GAP: #NN <reason>]` markers at the cited file:line locations. Do not proceed until resolved. |
| ABSTAIN | Insufficient evidence to bless the test spec. | Re-dispatch ×3 with the coverage matrix included; cap at 2 cycles → halt. |

### G4 — verification (per-ivy_verify-result)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | `ivy_verify` returned `status: OK`; no counterexamples; all invariants hold. | Append `gate_verdict{gate=g4, verdict=SOUND}`; refine workflow advances to its terminal phase. |
| UNSOUND(#NN, reason, isolate) | `ivy_verify` returned `status: FAIL` (counterexample present, invariant violation, or compile error). | Refine Phase 6 (Diagnose) is dispatched: read the counterexample, classify the failure pattern (#NN per `verification-failures` catalog), draft a fix candidate. |
| ABSTAIN | Verifier output ambiguous (timeout without counterexample, partial run). | Re-run `ivy_verify` with extended timeout once. On second ABSTAIN, halt and surface to user. |

### G5 — trace-analysis (per-IUT-run)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | IUT trace matches the formal model's expected behaviour; no protocol violation observed. | Append `gate_verdict{gate=g5, verdict=SOUND}`; the experiment workflow advances to its terminal phase. |
| UNSOUND(#NN, reason, spec-file:line) | Trace deviates from the model. The cite must reference the *spec* file:line, not the artifact path — the spec is the mutable target. | Write `[GAP: #NN <reason>]` markers at the cited spec locations. The hardest G5 call is distinguishing real IUT bugs from model bugs; when attribution is genuinely ambiguous, return ABSTAIN rather than commit to an incorrect story. |
| ABSTAIN | Critics could not establish attribution (real IUT bug vs. model bug). | Re-dispatch ×3 with the full artifact set (analysis_results.json, ivy_tester.log, IUT log, pcap via tshark). On second ABSTAIN, halt with caveat. |

### G6 — knowledge-capture (per-session)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | At least one candidate learning is novel, load-bearing, and portable enough to capture. | Per-candidate aggregation runs: ≥2 KEEP votes → append `knowledge_captured(...)` event with `confidence=high`; ≥2 DROP → no journal write; ≥2 DEFER (or 1-1-1 split) → AskUserQuestion(KEEP / DROP / SKIP) — KEEP writes with `confidence=user-confirmed`, DROP and SKIP do not write. |
| UNSOUND | No candidate is worth capturing this session (all are either already known, not load-bearing, or too session-specific to generalize). | No `knowledge_captured` events appended; `gate_verdict{gate=g6, verdict=UNSOUND}` is the journal trail for "we considered and rejected". |
| ABSTAIN | Critics could not vote (dispatch failed or all returned ABSTAIN). | Re-dispatch ×3; cap at 2 cycles → halt with `gate_verdict{gate=g6, verdict=ABSTAIN, abstain_reason="dispatch_failure"}`; user can re-trigger by manually emitting `pending_dispatch`. UX-cost note: G6 dispatches inline on cold-start-eligible session-resume turns (~90s wall-clock). Set `IVY_DISPATCH_G6=0` to opt out for the current session. |

### G7 — triage diagnose (per-MCP/LSP-failure)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Triage completed the 9-step runbook; root cause identified; repair successful. | Append `gate_verdict{gate=g7, verdict=SOUND}`; emit `pending_dispatch(<caller>, reason="post-triage-repair")` to hand control back to the caller. |
| UNSOUND(#NN, reason, runbook-step) | A runbook step failed without successful repair (e.g., MCP server cannot be revived; PID file remains stale). | Surface failure to user with the runbook step that failed. User decides: retry runbook, escalate, or abandon. |
| ABSTAIN | Diagnosis ambiguous (multiple plausible root causes; insufficient evidence to commit). | Re-diagnose with broader log capture; cap at 2 cycles → escalate to user. |

### G8 — triage repair-verify (per-repair-result)

| Verdict | Meaning | Routing |
|---|---|---|
| SOUND | Repair verified by re-running the failing tool; result matches expected pass shape. | Append `gate_verdict{gate=g8, verdict=SOUND}`; triage workflow terminates; `pending_dispatch(<caller>, reason="post-G8-repair-verified")` hands back. |
| UNSOUND | Repair verification failed (re-run still produces the original failure or a new failure). | Return to G7 diagnose with the new evidence. |
| ABSTAIN | Verification result inconclusive (intermittent failure, environmental flake). | Run verification 3× and aggregate; majority result wins. If still ABSTAIN, return with caveat and let user decide. |
