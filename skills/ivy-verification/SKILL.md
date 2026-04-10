---
name: Ivy Verification
description: This skill should be used when the user asks about "running formal verification", "ivy_check workflow", "verifying protocol specifications", "debugging verification failures", "interpreting ivy_check output", "invariant violations", "type safety errors", "verification debugging", or mentions checking Ivy models for correctness in the PANTHER Ivy framework.
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

**When verification fails, you MUST follow the `ivy-debugging-methodology` skill.** Do NOT attempt fixes without completing the pre-fix checklist (parse error → interpret diagnostics → consult skills → run linter → search examples → formulate theory → fix → verify).

For quick error lookups, consult the `ivy-error-patterns` skill which maps cryptic error messages to root causes, correct patterns, and working examples from `protocol-testing/`.

## Common Ivy Verification Errors and Fixes

> For the full error pattern catalog with working examples, see the `ivy-error-patterns` skill. The entries below are a quick reference subset.

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
