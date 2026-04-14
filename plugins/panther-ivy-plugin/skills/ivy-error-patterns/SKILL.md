---
name: ivy-error-patterns
description: "Error-to-fix lookup table for cryptic Ivy messages. Use when encountering \"not found\", \"ungrounded\", \"invariant failed\", \"type mismatch\", or any Ivy error."
user-invocable: false
---

# Ivy Error Patterns Reference

Lookup table for Ivy error messages. Each entry maps a cryptic error to its root cause and the correct fix.

## How to Use

1. Find the error message substring in the headings of `references/error-table.md`
2. Read the root cause and correct pattern
3. Check the working example to confirm the fix matches existing conventions
4. Apply the fix

## Top 5 Most Common Errors (Quick Reference)

| Error Substring | Root Cause | Fix |
|---|---|---|
| `'X' not found` | Parameter name collides with existing symbol | Use single uppercase letter params (`S:type`, `D:type`) |
| `ungrounded variable` | Free variable not bound by quantifier | Add explicit quantifier or ensure var appears in head |
| `invariant ... failed` | Action violates declared invariant | Add `require` guard, fix `after init`, or weaken invariant |
| `assumption failed` | Isolate assumption not satisfied by spec | Run `ivy_model_info`, check assumed isolate's guarantees |
| Missing `after init` | Relations start with arbitrary values | Add `after init { rel(X) := false; }` block |

For the full 12-entry lookup table with code examples and working references, see `references/error-table.md`.

## Related

- **`ivy-writing-guide`** — Language reference for correct patterns
- **`ivy-debugging-methodology`** — Pre-fix research workflow (run BEFORE applying fixes from this table)
- **`counterexample-guide`** — Trace interpretation for verification failures
