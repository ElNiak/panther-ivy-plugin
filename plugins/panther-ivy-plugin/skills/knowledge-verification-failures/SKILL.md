---
name: knowledge-verification-failures
description: "Use when ivy_verify FAIL, ivy_check failed, counterexample appears, or an adversarial gate cites pattern #NN. Owns numbered verifier-pattern catalog, debugging methodology, counterexample interpretation, and claim-resolution gate."
user-invocable: false
---

# Verification-Failure Knowledge

**Type:** flexible — adapt principles to context.

This skill consolidates four lifecycle-related knowledge surfaces invoked when verification produces signal: error-pattern lookup, the mandatory pre-fix debugging methodology, structured counterexample interpretation, and the claim-resolution gate that records the outcome inline. Use the section that matches your trigger; SKILL.md is a thin dispatcher and the procedural content lives in `references/`.

| Trigger | Section | Reference |
|---|---|---|
| Cryptic Ivy compile / verify error string (`'X' not found`, `ungrounded`, `invariant failed`, `type mismatch`); adversarial gate cites catalog `#NN` | [Error-pattern catalog](#error-pattern-catalog) | `references/verifier_patterns.md`, `references/error-table.md` |
| `ivy_verify` / `ivy_check` failed and a fix is being prepared | [Debugging methodology](#debugging-methodology) | `references/debugging-methodology.md` |
| `ivy_verify` output contains `counterexample` or `counterexample_trace` | [Counterexample interpretation](#counterexample-interpretation) | `references/counterexample-walkthrough.md` |
| `ivy_verify` FAIL, `ivy_coverage` shows gaps, or `model-reviewer` reports issues that need an inline resolution comment | [Claim-discussion gate](#claim-discussion-gate) | `references/verification-claim.md`, `references/mapping-claim.md`, `references/coverage-claim.md` |

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

---

## Error-pattern catalog

This section owns three reference files:

- **`references/verifier_patterns.md`** — the numbered, append-only catalog cited by adversarial quality gates G1–G5. Each entry carries a sparse ID preserving source provenance, a trigger condition, a check procedure, a source citation, and a methodology tag (`NCT` | `NACT` | `NSCT` | `Ivy` | `Plugin-Memory`). Catalog organisation is by lifecycle-gate ID range (`#100`–`#149` G1 / G5, `#150`–`#199` G1 NACT, `#200`–`#249` G2 / G3 / G4 Ivy decidability, `#250`–`#299` G2 / G3 / G4 plugin-memory, `#260`–`#289` G2 NSCT, `#300`–`#399` G3 test-spec, `#400`–`#499` G4 verdict, `#500`–`#559` G5 trace, `#560`–`#589` G5 NSCT). Each gate loads its range slice plus the methodology overlay indicated by `build-state.yaml:methodology`.
- **`references/error-table.md`** — the legacy quick-lookup table for cryptic Ivy error messages, kept for fast-path debugging. Includes the top-5 most common errors with root cause and fix.
- **`references/generator-patterns.md`** — pattern guide for Ivy test-traffic generators; anti-patterns (timer competition, two-step message construction, missing handle exports, over-constrained guards) and the correct patterns (auto-send, handle exports).

### How to use

**Cryptic Ivy error message** (e.g., `'X' not found`, `ungrounded variable`): load `references/error-table.md`, find the error substring, read root cause + fix, apply.

**Adversarial gate cites a catalog pattern** (e.g., `[GAP: #250]` marker, `gate_verdict` event names `#401`): load `references/verifier_patterns.md`, locate the entry by ID, read trigger / check / source, apply the fix pattern.

---

## Debugging methodology

For the mandatory 8-step pre-fix checklist (parse error → diagnostic interpretation → consult skills → structural check → search models → formulate theory → minimal fix → verify), Read `references/debugging-methodology.md`. Fixes proposed without evidence from this checklist are flagged UNSOUND by the G4 verification gate.

For C++ serializer / deserializer state-machine issues, the methodology routes you to `knowledge-ivy-writing-guide` → `references/serializer-patterns.md`.

For the self-evaluation protocol (anti-pattern checklist) and debug environment variables, Read `references/debugging-environment.md`. For the full 9-step health-check runbook (log paths, common failures, process liveness), dispatch the triage skill via `Skill(skill="panther-ivy-plugin:workflow-triage")`.

---

## Counterexample interpretation

When `ivy_verify` returns a verification failure with structured counterexample data (`counterexample` dict or `counterexample_trace` text), Read `references/counterexample-walkthrough.md` for:

- The 6-step interpretation workflow (read assertion → identify trace → trace state changes → look up symbol → view state machine → check coverage).
- The four common failure patterns with `Symptom` / `Trace signature` / `Root cause` / `Fix` for each (Missing Guard `#410`, Uninitialized State `#411`, Incorrect Monitor Scope `#412`, Invariant Too Strong `#413`).
- Fix-strategy summary table and lifecycle-placement decision matrix.

If verification fails but no counterexample is present, the failure is likely a type error, unresolved symbol, or Z3 timeout — load `knowledge-methodology-reference` instead.

For a complete end-to-end trace interpretation example, Read `references/trace-example.md`.

---

## Claim-discussion gate

Structured discussion templates for resolving verification claims, RFC mapping decisions, and coverage gap priorities. Select the template matching your trigger.

### Template selection

| Trigger | Template |
|---------|----------|
| `ivy_verify` FAIL or model-reviewer ERROR | `references/verification-claim.md` |
| `ivy_extract_requirements` or RFC mapping | `references/mapping-claim.md` |
| `ivy_coverage(mode="gaps")` shows uncovered reqs | `references/coverage-claim.md` |

After identifying the matching trigger, load the corresponding file.

### Persistence — inline resolution comments

All claim-discussion outcomes are recorded as inline comments in the source file. The date is always in ISO format (`YYYY-MM-DD`); the comment prefix matches the host file's syntax (`#` for `.ivy` and `.yaml`, `<!-- … -->` for `.md`). This parallels the `[GAP: …]` placement rules in `.claude/rules/gap-markers.md` — a resolution comment is the author-written successor to a gate-written GAP marker.

```ivy
require conn_state = open;  # [rfc9000:4.1] RESOLVED(2026-03-18): Confirmed spec-correct per user
```

| Prefix | Meaning |
|--------|---------|
| `RESOLVED({date})` | Claim discussed and confirmed correct |
| `IUT_FINDING({date})` | IUT non-compliance identified |
| `GUARD_ADDED({date})` | Generation guard added per discussion |
| `DEFERRED({date})` | Decision postponed with reason |
| `KNOWN_DEVIATION({date})` | IUT intentionally diverges from spec |
| `N/A({date})` | Requirement not applicable with reason |

Rules:

- Keep comments concise (one line).
- Place on the same line as the assertion when possible.
- Never remove existing resolution comments — append if revisiting.

---

## Integration

- **Loaded by:** `workflow-verify` (Phase 6 Diagnose), `workflow-build` (Phase 3 on compile error), `workflow-review` (Phase 3 on contested findings); G4 verification critics, G5 trace-analysis critics, and the `model-reviewer` / `spec-analyst` agents during their dispatch phases.
- **Precedes:** the G4 verification gate cites `references/debugging-methodology.md` (catalog entry `#405`); fixes proposed without those steps are UNSOUND by gate criteria.

**Related skills:** `knowledge-ivy-writing-guide` (language reference), `knowledge-ivy-toolkit` (MCP tool inventory), `knowledge-methodology-reference` (verification-cycle context, per-methodology counterexample interpretation), `cross-cutting-reflection-patterns` (adversarial-gate discipline layer).

**Related agents:** `spec-analyst` (automated diagnosis — consumes the catalog and the debugging methodology), `model-reviewer` (adversarial review — consumes the catalog and the claim-discussion templates).

**MCP tools used:** `ivy_verify` (counterexample source), `ivy_diagnostics` (structural check + full diagnostic array), `ivy_model_info` (symbol look-up), `ivy_visualize(view="state_machine")` (state-transition view), `ivy_coverage(mode="gaps")` (gap discovery); LSP `hover` / `findReferences` / `goToDefinition` (symbol look-up across includes).
