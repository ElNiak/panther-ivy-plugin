---
name: verification-failures
description: "Use when ivy_verify FAIL, ivy_check failed, counterexample appears, or an adversarial gate cites pattern #NN. Owns numbered verifier-pattern catalog, debugging methodology, counterexample interpretation, and claim-resolution gate."
user-invocable: false
---

# Verification-Failure Knowledge

**Type:** flexible — adapt principles to context.

This skill consolidates four lifecycle-related knowledge surfaces invoked when verification produces signal: error-pattern lookup, the mandatory pre-fix debugging methodology, structured counterexample interpretation, and the claim-resolution gate that records the outcome inline. SKILL.md is a thin dispatcher; procedural content lives in `references/`. Set the active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

| Trigger | Reference to load |
|---|---|
| Cryptic Ivy compile / verify error string (`'X' not found`, `ungrounded`, `invariant failed`, `type mismatch`); adversarial gate cites catalog `#NN` | `references/verifier_patterns.md`, `references/error-table.md` |
| `ivy_verify` / `ivy_check` failed and a fix is being prepared | `references/debugging-methodology.md` |
| `ivy_verify` output contains `counterexample` or `counterexample_trace` | `references/counterexample-walkthrough.md` |
| `ivy_verify` FAIL, `ivy_coverage` shows gaps, or `model-reviewer` reports issues that need an inline resolution comment | `references/verification-claim.md`, `references/mapping-claim.md`, `references/coverage-claim.md` |

## References

- `references/verifier_patterns.md` — numbered, append-only catalog cited by adversarial quality gates G1–G5; sparse IDs by lifecycle-gate range (`#100-149` G1/G5, `#150-199` G1 NACT, `#200-249` G2/G3/G4 Ivy decidability, `#250-299` G2/G3/G4 plugin-memory, `#260-289` G2 NSCT, `#300-399` G3 test-spec, `#400-499` G4 verdict, `#500-559` G5 trace, `#560-589` G5 NSCT). Each gate loads its range slice plus the methodology overlay indicated by `build-state.yaml:methodology`.
- `references/error-table.md` — legacy quick-lookup table for cryptic Ivy error messages, kept for fast-path debugging; top-5 most common errors with root cause and fix.
- `references/debugging-methodology.md` — mandatory 8-step pre-fix checklist (parse error → diagnostic interpretation → consult skills → structural check → search models → formulate theory → minimal fix → verify). Fixes proposed without evidence from this checklist are flagged UNSOUND by the G4 verification gate.
- `references/debugging-environment.md` — self-evaluation protocol (anti-pattern checklist) and debug environment variables.
- `references/counterexample-walkthrough.md` — 6-step interpretation workflow plus the four common failure patterns with `Symptom`/`Trace signature`/`Root cause`/`Fix` (Missing Guard `#410`, Uninitialized State `#411`, Incorrect Monitor Scope `#412`, Invariant Too Strong `#413`); fix-strategy summary table and lifecycle-placement decision matrix.
- `references/trace-example.md` — complete end-to-end trace interpretation example.
- `references/generator-patterns.md` — pattern guide for Ivy test-traffic generators; anti-patterns (timer competition, two-step message construction, missing handle exports, over-constrained guards) and correct patterns (auto-send, handle exports).
- `references/verification-claim.md` — claim-discussion template for `ivy_verify` FAIL or model-reviewer ERROR; includes the inline resolution-comment conventions (RESOLVED / IUT_FINDING / GUARD_ADDED / DEFERRED / KNOWN_DEVIATION / N/A).
- `references/mapping-claim.md` — claim-discussion template for `ivy_extract_requirements` or RFC mapping decisions.
- `references/coverage-claim.md` — claim-discussion template for `ivy_coverage(mode="gaps")` results.

If verification fails but no counterexample is present, the failure is likely a type error, unresolved symbol, or Z3 timeout — load `methodology` instead. For C++ serializer / deserializer state-machine issues, the methodology routes to `ivy-syntax` → `references/serializer-patterns.md`. For the full 9-step health-check runbook (log paths, common failures, process liveness), dispatch the triage skill via `Skill(skill="panther-ivy-plugin:workflow-triage")`.

## Integration

- **Loaded by:** `workflow-verify` (Phase 6 Diagnose), `workflow-build` (Phase 3 on compile error), `workflow-review` (Phase 3 on contested findings); G4 verification critics, G5 trace-analysis critics, and the `model-reviewer` / `spec-analyst` agents during their dispatch phases.
- **Precedes:** the G4 verification gate cites `references/debugging-methodology.md` (catalog entry `#405`); fixes proposed without those steps are UNSOUND by gate criteria.

**Related skills:** `ivy-syntax` (language reference), `ivy-toolkit` (MCP tool inventory), `methodology` (verification-cycle context, per-methodology counterexample interpretation), `cross-cutting-reflection-patterns` (adversarial-gate discipline layer).

**Related agents:** `spec-analyst` (automated diagnosis — consumes the catalog and the debugging methodology), `model-reviewer` (adversarial review — consumes the catalog and the claim-discussion templates).

**MCP tools used:** `ivy_verify` (counterexample source), `ivy_diagnostics` (structural check + full diagnostic array), `ivy_model_info` (symbol look-up), `ivy_visualize(view="state_machine")` (state-transition view), `ivy_coverage(mode="gaps")` (gap discovery); LSP `hover` / `findReferences` / `goToDefinition` (symbol look-up across includes).
