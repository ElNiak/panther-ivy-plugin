---
name: ivy-verification
description: "Ivy verification reference — running ivy_verify and ivy_lint, interpreting results, diagnosing failures. Use when verifying an Ivy spec, interpreting a verification failure, or deciding which tool to run. Triggers on 'verify', 'ivy_check failed', 'invariant failed', 'safety property violated', 'verification error', 'check my spec', 'run verification'."
context: fork
---

# Ivy Verification Reference

This skill covers the verification workflow: which tools to run, in what order, and how to interpret results.

---

## Tool Selection

| Goal | Tool | Notes |
|------|------|-------|
| Fast structural check (milliseconds) | `ivy_lint` | Catches missing headers, braces, includes, parameter collisions |
| Formal property verification | `ivy_verify` | Checks isolates, invariants, safety properties |
| Compile to test binary | `ivy_compile` | `target=test` |
| Model introspection | `ivy_model_info` | Lists types, relations, actions, isolates |

**Always run `ivy_lint` before `ivy_verify`.** Structural issues produce misleading verification errors.

---

## Debugging Workflow

**When verification fails, you MUST follow the `ivy-debugging-methodology` skill.** Do NOT attempt fixes without completing the pre-fix checklist (parse error → interpret diagnostics → consult skills → run linter → search examples → formulate theory → fix → verify).

For quick error lookups, consult the `ivy-error-patterns` skill which maps cryptic error messages to root causes, correct patterns, and working examples from `protocol-testing/`.

---

## Common Ivy Verification Errors and Fixes

> For the full error pattern catalog with working examples, see the `ivy-error-patterns` skill. The entries below are a quick reference subset.

### "failed to verify" on an action body

Ivy could not prove a `require` or `ensure` clause in an action body.

**Steps:**
1. Identify the failing action and clause from the error output
2. Check if a precondition is missing (add `require` guards)
3. Check if an invariant needs strengthening
4. Search `protocol-testing/` for similar actions: `Grep(pattern="action <name>", glob="*.ivy")`

**Related:** `ivy-error-patterns` entry #3

---

### "invariant ... failed" / "failed to verify invariant preservation"

An action modifies state in a way that violates a declared invariant.

**Steps:**
1. Identify which action violates the invariant (the counterexample trace shows this)
2. Check that all state updates in the action are consistent with the invariant
3. Add `require` guards to restrict the action to states where the invariant can be maintained
4. Verify `after init` initializes state compatibly with the invariant

**Related:** `ivy-error-patterns` entry #3, entry #12

---

### "assumption failed" (isolate assumption violation)

An isolate's assumptions about another isolate's behavior are not satisfied.

**Steps:**
1. Run `ivy_model_info` to list isolates and their assumptions
2. Strengthen the assumed isolate's specification, or weaken the assumption

**Related:** `ivy-error-patterns` entry #4

---

### "type error" / "type mismatch"

Incompatible types in an expression.

**Steps:**
1. Identify the expression with the mismatch from the error line
2. Read type declarations with `Read` or `ivy_model_info`
3. Ensure all usages match the declared type

**Related:** `ivy-error-patterns` entry #5

---

### "'<name>' not found" on declaration

A parameter name is being resolved as a symbol reference and failing.

**Immediate fix**: Rename all multi-character lowercase parameter names to single uppercase letters (C, S, P, N, D).

**Related:** `ivy-error-patterns` entry #1

---

### Z3 timeout / "unknown"

The SMT solver cannot decide within resource limits.

**Steps:**
1. Break the isolate into smaller pieces
2. Add auxiliary invariants (lemmas) to guide the prover
3. Reduce quantifier nesting depth
4. Use `isolate` boundaries to limit solver scope

**Related:** `ivy-error-patterns` entry #9

---

## Verification Result Interpretation

### Reading the `diagnostics` Array

When `ivy_verify` or `ivy_lint` returns a failure, read the full `diagnostics` array, not just `error_summary`. Each diagnostic has:

| Field | Meaning |
|-------|---------|
| `source` | Layer: `"ivy"` (parser), `"z3"` (solver), `"ivy-lsp"` (structural) |
| `severity` | `"error"`, `"warning"`, `"info"` |
| `line` | Source line number |
| `message` | The error text — look this up in `ivy-error-patterns` |

### Return Codes

| Return Code | Meaning |
|-------------|---------|
| 0 | All checks pass |
| Non-zero | Failures detected — read diagnostics |

---

## Verification Checklist (Self-Evaluation)

After writing or modifying an Ivy specification, run in this order:

1. **`ivy_lint`** — fast structural check (milliseconds). Fix: missing `#lang`, unresolved includes, unmatched braces, parameter name collisions.
2. **`ivy_verify`** — formal property verification. If FAIL: read error line → locate with Grep/LSP go-to-definition → look up in `ivy-error-patterns` → diagnose → fix → re-verify.
3. **`ivy_coverage`** (mode="stats") — check MUST requirement coverage. Add missing `before`/`after` monitors with bracket tags if low.
4. **Anti-pattern checklist** — before declaring complete:
   - Missing `after init` → relations start with arbitrary values
   - Ungrounded variables in invariants → `invariant sent(P, N)` means "for ALL P and N"
   - `assume` instead of `require` → weakens the model
   - Missing `require` in `before` clauses → actions callable in any state
   - Multi-character lowercase parameter names → symbol resolution errors
   - Circular include dependencies → DAG required

---

## Integration

**Related skills:**
- **ivy-debugging-methodology** — mandatory pre-fix checklist (MUST follow before any fix)
- **ivy-error-patterns** — full error catalog with working examples
- **ivy-model-editing** — language reference for writing/editing declarations
- **counterexample-guide** — trace interpretation for invariant failures
- **ivy-toolkit** — MCP tool documentation and invocation patterns

**Related agents:**
- **spec-analyst** — verification diagnosis and structured result presentation
- **model-reviewer** — model quality review

**IMPORTANT**: Always use ivy-tools MCP tools for verification and compilation — never invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` via Bash. See `ivy-toolkit` skill for tool selection.
