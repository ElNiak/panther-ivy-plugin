---
name: ivy-verification
description: Use when running ivy_verify, interpreting verification failures, or debugging invariant violations, type errors, and Z3 timeouts
---

# Ivy Verification Workflow

## Overview

Ivy is a formal specification language used for modeling and verifying protocol implementations.
The primary verification tool is `ivy_check`, which statically checks Ivy models for type safety,
invariant preservation, and protocol correctness.

## Running Verification

### Using ivy-tools MCP tools (required)

Always use the ivy-tools MCP tools for verification. Never run `ivy_check` directly via Bash.

**Full model check:**
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with `relative_path` pointing to the `.ivy` file.

**Specific isolate check** (faster, targets one component):
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with `relative_path` and `isolate` parameters.

**Model structure inspection:**
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` to understand model structure before verification.

### Verification via Plugin Commands

- `/nct-check <file>` — Run formal verification on an .ivy file
- `/nct-check <file> --isolate <name>` — Check a specific isolate

## Interpreting Results

### Successful Verification

A successful check produces output containing `OK` or lists each checked isolate with `OK` status. This means all proof obligations were discharged.

### Verification Failures

Failures include:
- **Line numbers** pointing to the failing assertion or action
- **Counterexample traces** showing a sequence of actions leading to the failure
- **Error type** indicating what went wrong

Common failure patterns:

1. **Invariant not preserved** — an action modifies state in a way that violates a declared invariant.
   ```
   error: failed to verify invariant preservation in action client.send
   ```
   Fix: strengthen the invariant, add preconditions to the action, or fix the action logic.

2. **Type safety error** — a value is used with an incompatible type.
   ```
   error: type mismatch at line 42: expected packet_type, got nat
   ```
   Fix: ensure all variables and expressions have consistent types.

3. **Ungrounded relation** — a relation is used in a way that leaves variables unbound.
   ```
   error: ungrounded variable X in relation recv(X,Y)
   ```
   Fix: ensure all variables in relation expressions are bound by quantifiers or appear in the head.

4. **Safety property violation** — an exported action can reach an unsafe state.
   ```
   error: safety property violated at line 85
   ```
   Fix: add missing invariants, strengthen preconditions, or fix the protocol logic.

5. **Liveness/progress failure** — the model cannot guarantee progress.
   Fix: check for deadlock scenarios and add fairness assumptions if appropriate.

## Debugging Workflow

Follow this cycle when verification fails:

1. **Check**: Run verification via `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`.
2. **Read the error**: Note the line number, error type, and any counterexample trace.
3. **Locate the issue**: Use Claude's `Grep` tool or native LSP go-to-definition to navigate to the failing symbol.
4. **Diagnose**: Determine if the issue is:
   - A missing invariant (the model under-specifies expected behavior)
   - A bug in the action logic (the model is incorrect)
   - A missing precondition (the action is called in unexpected contexts)
5. **Fix**: Apply the minimal fix using Claude's `Edit` tool. Prefer adding invariants over weakening specifications.
6. **Re-check**: Run verification again. Repeat until all checks pass.

## Common Ivy Verification Errors and Fixes

### "failed to verify" on an action body
The action's postcondition or an invariant is not maintained. Check:
- Are all modified relations updated consistently?
- Does the action's `ensure` clause match what the body actually does?

### "cannot find isolate X"
The isolate name is misspelled or not declared. Check:
- Spelling of the isolate name in the command and in the `.ivy` file.
- That the isolate is declared with `isolate X = { ... }` or `object X = { ... }` with `specification` or `implementation` keywords.

### "circular dependency"
Two or more modules or objects depend on each other. Fix:
- Refactor to break the cycle, typically by introducing an abstract interface.

### "uninterpreted sort has no instances"
A type was declared but never given concrete values. Fix:
- Add at least one constructor or axiom that provides instances of the sort.

### Z3 timeout or "unknown" result
The SMT solver could not decide within the time limit. Fix:
- Simplify the proof obligation by breaking it into smaller lemmas.
- Add ghost state or auxiliary invariants to guide the prover.
- Use `isolate` boundaries to limit what the solver must reason about.

**IMPORTANT**: Always use ivy-tools MCP tools for Ivy verification operations. Never run ivy_check, ivyc, ivy_show, or ivy_to_cpp directly via Bash. Use `/nct-check`, `/nct-compile`, or `/nct-model-info` commands.

## Red Flags -- STOP

| Rationalization | Reality |
|----------------|---------|
| "Verification passed last time, it should still pass" | Run it. Previous results prove nothing about current state. |
| "This change is too small to break anything" | Small changes break invariants. Verify. |
| "Z3 timed out, so the model is probably fine" | Timeout means unknown, not OK. Simplify or add lemmas. |
| "I can assume this invariant holds" | Use `require`, not `assume`. `assume` weakens the model unsoundly. |
| "The error is in a different isolate, I can ignore it" | Isolate failures can cascade. Fix before proceeding. |
| "I'll fix the verification failure after finishing the feature" | Never proceed with broken verification. Fix it now. |

## Common Mistakes

**Using `assume` instead of `require`**
- **Problem:** `assume` tells the solver "pretend this is true" — it makes the model unsound
- **Fix:** Use `require` for preconditions. Only use `assume` when you have a proven lemma.

**Ungrounded variables in invariants**
- **Problem:** `invariant sent(P, N)` means "for ALL P and N, sent is true" — almost always wrong
- **Fix:** Ground variables: `invariant sent(P, N) -> P = the_cid`

## Integration

**Prerequisite skills:**
- **panther-ivy:ivy-tooling-guide** — Understanding MCP tool architecture

**Follow-up skills:**
- **panther-ivy:writing-test-specs** — After verification passes, write test specs

**Related agents:**
- **spec-verifier** — Automated verification workflow
- **ivy-model-reviewer** — Model quality review

**Related commands:**
- `/nct-check` — Quick verification shortcut
