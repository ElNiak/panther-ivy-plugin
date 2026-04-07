---
name: counterexample-guide
description: Use when ivy_verify fails with a counterexample to understand the failure, trace the violated property, and identify the fix. Guides interpretation of structured counterexample traces.
loads: [ivy-writing-guide, workflow-reference]
prerequisites:
  - ivy-writing-guide
  - workflow-reference
---

# Counterexample Interpretation Guide

When `ivy_verify` returns a verification failure, it may include structured counterexample data that shows exactly how the property was violated. This skill provides a systematic workflow for reading counterexample traces, diagnosing the root cause, and applying the correct fix.

---

## When to Use

Use this skill when `ivy_verify` output contains either of these fields:

- **`counterexample`**: Structured dict with `assertion`, `assertion_line`, and `steps` (parsed from raw ivy_check output)
- **`counterexample_trace`**: Human-readable formatted trace with step-by-step state changes

If the verification fails but no counterexample is present, the failure is likely a type error, unresolved symbol, or Z3 timeout -- use the `workflow-reference` skill instead for those cases.

---

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

## Interpretation Workflow

Follow these steps in order when you receive a counterexample.

### Step 1: Read the Violated Assertion

Look at the `counterexample_trace` field first. The header tells you what failed:

```
Violated assertion (Line 42):
  require conn_seen(C)
```

This gives you:
- **Line number**: Where the failing `require`/`assert`/`ensure` lives
- **Assertion text**: The property that the solver proved can be violated

Use `Read` to view the assertion in context (surrounding before/after block, action signature).

### Step 2: Identify the Execution Trace

The trace shows the sequence of actions that led to the violation:

```
Execution trace (2 steps):
--------------------------------------------------

  Step 1: quic_connection.open
    conn_seen = false
    cid = 0x1234

  Step 2: quic_stream.send
    conn_seen = false
    stream_state = open  (was: idle)
    bytes_sent = 0
```

Each step shows:
- **Action name**: The protocol event that fired
- **Variable assignments**: State after this step executed
- **Change markers**: `(was: X)` indicates a variable that changed from a previous step

### Step 3: Trace State Variable Changes

Walk through the steps and look for:
1. **Variables that never change when they should** -- e.g., `conn_seen` stays `false` across all steps, but the assertion expects it to be `true` after `quic_connection.open`
2. **Variables that change unexpectedly** -- marked with `(was: X)`, indicating a state transition happened
3. **Missing steps** -- if you expect an intermediate action (like a handshake) but it does not appear, a guard may be too permissive

### Step 4: Look Up the Violated Symbol

Use `ivy_model_info` to understand the symbol's definition, or `Grep` to find its declaration across include files.

### Step 5: View State Machine Context

Use the state machine view to see the broader state transition picture:

```
ivy_visualize(view="state_machine", test_file="path/to/test.ivy")
```

This shows all states and transitions, helping you spot whether the counterexample trace represents a valid but unguarded path through the state machine.

### Step 6: Check Related Coverage

Use coverage analysis to find related gaps:

```
ivy_coverage(mode="gaps", test_file="path/to/test.ivy")
```

Look for unguarded state variables or orphaned monitors that relate to the failing assertion. The counterexample often exploits a gap that this tool can identify.

---

## Common Failure Patterns

### 1. Missing Guard

**Symptom**: The counterexample reaches an action without a required precondition being true.

**Trace signature**: A variable the assertion depends on is never set to the expected value because the action fired without the necessary `require` guard.

```
Step 1: stream.send        <-- fires without connection being established
  connected = false         <-- should be guarded: require connected(the_cid)
```

**Root cause**: A `before` block is missing a `require` statement, or the `require` does not cover all necessary preconditions.

**Fix**: Add the missing `require` to the `before` block:

```ivy
before stream.send(id:stream_id, data:stream_data) {
    require connected(the_cid);            # Add missing guard
    require stream_state(id) = open;       # Add missing guard
}
```

### 2. Uninitialized State

**Symptom**: A state variable has an unexpected value in Step 1 (the very first step), before any action has modified it.

**Trace signature**: A relation or function has an arbitrary value because no `after init` block sets it.

```
Step 1: packet_event
  conn_state = closed       <-- expected: should be initialized to 'idle'
```

**Root cause**: The specification does not include an `after init` block for this state variable, so Ivy treats it as unconstrained (any value is possible).

**Fix**: Add initialization:

```ivy
after init {
    conn_state(C) := idle;           # Initialize for all connection IDs
    conn_seen(C) := false;           # Initialize boolean relation
}
```

### 3. Incorrect Monitor Scope

**Symptom**: A monitor triggers on the wrong action, or a `before`/`after` block is attached to the wrong event.

**Trace signature**: The counterexample shows an action firing that should have been constrained, but the constraint is on a *different* action.

```
Step 1: frame.rst_stream.handle     <-- this action is unconstrained
  stream_state = open                <-- violation: should require stream_state = sending
```

Meanwhile, the `require` guard exists but is attached to `frame.stream.handle` instead of `frame.rst_stream.handle`.

**Root cause**: The `before`/`after` monitor watches the wrong action, or uses the wrong `mixin_kind` (e.g., `before` when `after` is needed for state update checks).

**Fix**: Move or duplicate the constraint to the correct action:

```ivy
before frame.rst_stream.handle(f:frame.rst_stream, scid:cid, dcid:cid) {
    require stream_state(f.id) = sending;    # Guard on the correct action
}
```

### 4. Invariant Too Strong

**Symptom**: The invariant asserts something that is temporarily false during a legitimate state transition, and the counterexample catches the transient state.

**Trace signature**: The state is correct at the start and end of a multi-step sequence, but the invariant fires during an intermediate step.

```
Step 1: connection.open
  handshake_done = false       <-- invariant: require handshake_done -> data_sent
  data_sent = false            <-- OK: both false, implication holds

Step 2: connection.handshake_complete
  handshake_done = true  (was: false)
  data_sent = false            <-- VIOLATION: handshake_done is true but data_sent is still false
```

**Root cause**: The invariant `handshake_done -> data_sent` is too strong -- it does not account for the state between handshake completion and the first data send.

**Fix options**:
- **Weaken the invariant**: `handshake_done & ~in_handshake_transition -> data_sent`
- **Restructure**: Move the check to `_finalize` instead of an invariant, so it only checks end-state
- **Add intermediate state**: Introduce a guard variable that tracks the transition phase

---

## Fix Strategies

### Add or Strengthen Guard Conditions

When the counterexample shows an action firing in an invalid state, add `require` statements to the `before` block:

```ivy
before action_name(...) {
    require precondition_1;
    require precondition_2;
    if _generating {
        require additional_test_generation_constraint;
    }
}
```

Use `ivy_coverage(mode="gaps")` to find other state variables that may also need guards.

### Add State Initialization

When the counterexample shows an unexpected initial value, add `after init` blocks. Check **all** state variables used in the failing assertion:

```ivy
after init {
    relation_name(X) := false;
    function_name(X) := default_value;
}
```

### Split Monitors into Finer-Grained Boundaries

When a single monitor tries to handle too many cases, split it into per-action monitors:

```ivy
# Instead of one broad monitor on packet_event:
before frame.stream.handle(f, scid, dcid, e) { ... }
before frame.ack.handle(f, scid, dcid, e) { ... }
before frame.rst_stream.handle(f, scid, dcid, e) { ... }
```

### Move Checks to Appropriate Lifecycle Points

| Check Type | Where to Place |
|---|---|
| Preconditions (must hold before action) | `before` block with `require` |
| State updates (record what happened) | `after` block with assignment |
| Compliance checks (verify response) | `after` block with `require` |
| End-state properties (hold at test end) | `_finalize` action |
| Always-true properties | `invariant` (use sparingly) |

---

## Example: Reading a Counterexample and Identifying the Fix

### Scenario

`ivy_verify` fails on `quic_server_test_stream.ivy` with this `counterexample_trace`:

```
Violated assertion (Line 87):
  require stream_data_sent(S)

Execution trace (3 steps):
--------------------------------------------------

  Step 1: quic_connection.open
    conn_seen = true
    cid = 0xABCD
    connected = true

  Step 2: frame.stream.handle
    stream_id = 4
    stream_state = idle  (was: idle)
    bytes_sent = 0

  Step 3: _finalize
    stream_data_sent = false
```

### Diagnosis

1. **Violated assertion**: `require stream_data_sent(S)` at line 87, inside `_finalize`
2. **Step 2 observation**: `stream_state` stays `idle` -- it was never transitioned to `open` or `sending`. The `bytes_sent = 0` confirms no data was actually sent.
3. **Root cause**: `frame.stream.handle` fires but does not update `stream_data_sent` or `stream_state`. The `after` block for `frame.stream.handle` is missing the state update, or the `before` block does not require `f.length > 0` to ensure meaningful data.

### Investigation

Use LSP `hover` on the `stream_data_sent` symbol to get its type info, then `findReferences` to see where it is set.

This reveals `stream_data_sent` is set in `after frame.stream.handle` only when `f.length > 0`, but no `before` guard requires `f.length > 0` during test generation.

### Fix

Add a generation guard to ensure the test mirror only generates meaningful stream frames:

```ivy
before frame.stream.handle(f:frame.stream, scid:cid, dcid:cid, e:quic_packet_type) {
    if _generating {
        require f.length > 0;                 # Ensure non-empty stream data
        require stream_state(f.id) = open;    # Ensure stream is open
    }
}
```

After applying the fix, re-run `ivy_verify` to confirm the counterexample is resolved.

---

## Integration

- **USED BY:** spec-analyst/model-reviewer agents (typically during orchestrator Phase 4)

**Prerequisite:** `ivy-writing-guide` -- Understanding Ivy syntax for before/after monitors, invariants, and state variables.

**Related skills:**
- **workflow-reference** -- General verification debugging cycle and error taxonomy
- **ivy-toolkit** -- MCP tool documentation (see references/tool-catalog.md)
- **ivy-writing-guide** -- Ivy syntax for before/after monitors, invariants, state variables

**Related agents:**
- **spec-analyst** -- Automated verification and diagnosis

**MCP tools used in this workflow:**
- `ivy_verify` -- Run verification (source of counterexamples)
- LSP `hover` / `findReferences` / `goToDefinition` -- Look up symbol definitions and usages
- `ivy_visualize` (view="state_machine") -- View state transitions
- `ivy_coverage` (mode="gaps") -- Find related unguarded state

## Related Skills

- **`claim-discussion`** — Structured decision trees for verification claims, RFC interpretations, and coverage gaps. Use after diagnosing a counterexample to decide whether it reveals a spec bug or IUT non-compliance.
- **`workflow-reference`** — The full verify-fix cycle (check → diagnose → fix → re-check). Provides quality gates and RFC-to-Ivy mapping context.
