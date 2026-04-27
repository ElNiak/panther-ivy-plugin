---
name: ivy-error-patterns
description: "Use when hitting Ivy errors ('not found', 'ungrounded', 'invariant failed', 'type mismatch') or when an adversarial gate cites catalog pattern #NN. Numbered verifier-patterns catalog plus error lookup."
user-invocable: false
---

# Ivy Error Patterns & Verifier Catalog

**Type:** flexible — adapt principles to context.

This skill owns three related reference files:

- **`references/verifier_patterns.md`** — the numbered, append-only catalog cited by adversarial quality gates G1–G5. Each entry carries a sparse ID preserving source provenance, a trigger condition, a check procedure, a source citation, and a methodology tag (`NCT` | `NACT` | `NSCT` | `Ivy` | `Plugin-Memory`).
- **`references/error-table.md`** — the legacy quick-lookup table for cryptic Ivy error messages, kept for fast-path debugging.
- **`references/generator-patterns.md`** — pattern guide for Ivy test-traffic generators; anti-patterns (timer competition, two-step message construction, missing handle exports, over-constrained guards) and the correct patterns (auto-send, handle exports).

## How to Use

**When debugging a cryptic Ivy error message** (e.g., you just saw `'X' not found` or `ungrounded variable` in compiler output):

1. Load `references/error-table.md` and find the error substring in its headings.
2. Read the root cause and correct pattern.
3. Check the working example to confirm the fix matches existing conventions.
4. Apply the fix.

**When an adversarial gate cites a catalog pattern** (e.g., a `[GAP: #250 missing re-entry guard]` marker appears in a spec, or a `gate_verdict` event names `#401`):

1. Load `references/verifier_patterns.md` and locate the entry by ID.
2. Read the trigger, what to check, and the cited source.
3. If the source is a `feedback_*` memory ID, consult the plugin memory for additional context.
4. Apply the fix pattern in place.

## Top 5 Most Common Errors (Quick Reference)

| Error Substring | Root Cause | Fix |
|---|---|---|
| `'X' not found` | Parameter name collides with existing symbol | Use single uppercase letter params (`S:type`, `D:type`) |
| `ungrounded variable` | Free variable not bound by quantifier | Add explicit quantifier or ensure var appears in head |
| `invariant ... failed` | Action violates declared invariant | Add `require` guard, fix `after init`, or weaken invariant |
| `assumption failed` | Isolate assumption not satisfied by spec | Run `ivy_model_info`, check assumed isolate's guarantees |
| Missing `after init` | Relations start with arbitrary values | Add `after init { rel(X) := false; }` block |

## Catalog overview

`references/verifier_patterns.md` organizes entries by lifecycle-gate ID range:

| Range | Gate(s) | Topic |
|---|---|---|
| #100-149 | G1, G5 | NCT base lifecycle failures |
| #150-199 | G1 | NACT attacker-model and mutation failures (NACT overlay) |
| #200-249 | G2, G3, G4 | Ivy decidability and testing-tutorial patterns |
| #250-299 | G2, G3, G4 | Plugin-memory migrations |
| #260-289 | G2 | NSCT timer and topology (NSCT overlay) |
| #300-399 | G3 | Test-spec authoring patterns |
| #400-499 | G4 | Verification verdict patterns |
| #500-559 | G5 | Trace-analysis patterns |
| #560-589 | G5 | NSCT replay and syscall (NSCT overlay) |

Each gate loads only its range slice plus the methodology overlay indicated by `build-state.yaml:methodology`. See `references/verifier_patterns.md` for the per-gate slice list.

## Related

- **`ivy-writing-guide`** — Language reference for correct patterns.
- **`ivy-debugging-methodology`** — Pre-fix research workflow (run BEFORE applying fixes).
- **`counterexample-guide`** — Trace interpretation for verification failures; its four named patterns are catalogued as #410-413.
- **`reflection-patterns`** — Adversarial-gate discipline layer; references this catalog from every gate's critic prompt.
