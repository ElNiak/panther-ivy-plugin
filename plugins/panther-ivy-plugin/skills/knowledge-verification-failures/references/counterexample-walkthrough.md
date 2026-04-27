# Counterexample interpretation walkthrough

Step-by-step workflow for reading counterexample traces, diagnosing the root cause, and applying the correct fix. The host skill (`knowledge-verification-failures`) points here when `ivy_verify` output contains `counterexample` or `counterexample_trace`.

## When this walkthrough applies

Use this walkthrough when `ivy_verify` output contains either:

- **`counterexample`**: structured dict with `assertion`, `assertion_line`, and `steps` (parsed from raw `ivy_check` output).
- **`counterexample_trace`**: human-readable formatted trace with step-by-step state changes.

If verification fails but no counterexample is present, the failure is likely a type error, unresolved symbol, or Z3 timeout — load the `knowledge-methodology-reference` skill instead.

**Methodology note.** Under NCT the default interpretation of a counterexample is *the IUT-side spec violates a compliance invariant*. Under NACT the perspective flips: a counterexample typically means *the attacker cannot reach a state the attack model claims is reachable* (i.e. the attack model is over-constrained). Under NSCT, counterexamples also need to be weighed against the seed / replay context (see `knowledge-methodology-reference` for the per-methodology interpretation decision tree).

## Interpretation workflow

### Step 1: Read the violated assertion

Look at the `counterexample_trace` field first. The header tells you what failed:

```
Violated assertion (Line 42):
  require conn_seen(C)
```

This gives you:

- **Line number**: where the failing `require` / `assert` / `ensure` lives.
- **Assertion text**: the property that the solver proved can be violated.

Use `Read` to view the assertion in context (surrounding `before` / `after` block, action signature).

### Step 2: Identify the execution trace

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

- **Action name**: the protocol event that fired.
- **Variable assignments**: state after this step executed.
- **Change markers**: `(was: X)` indicates a variable that changed from a previous step.

### Step 3: Trace state variable changes

Walk through the steps and look for:

1. **Variables that never change when they should** — e.g., `conn_seen` stays `false` across all steps, but the assertion expects it to be `true` after `quic_connection.open`.
2. **Variables that change unexpectedly** — marked with `(was: X)`, indicating a state transition happened.
3. **Missing steps** — if you expect an intermediate action (like a handshake) but it does not appear, a guard may be too permissive.

### Step 4: Look up the violated symbol

Use `ivy_model_info` to understand the symbol's definition, or `Grep` to find its declaration across include files.

### Step 5: View state machine context

```
ivy_visualize(view="state_machine", test_file="path/to/test.ivy")
```

This shows all states and transitions, helping you spot whether the counterexample trace represents a valid but unguarded path through the state machine.

### Step 6: Check related coverage

```
ivy_coverage(mode="gaps", test_file="path/to/test.ivy")
```

Look for unguarded state variables or orphaned monitors that relate to the failing assertion. The counterexample often exploits a gap that this tool can identify.

## Common failure patterns

Each of the four patterns below is catalogued (with IDs `#410`–`#413`) in `verifier_patterns.md` (sibling reference) for adversarial-gate citation:

| Pattern | Catalog ID |
|---|---|
| Missing Guard | `#410` |
| Uninitialized State | `#411` |
| Incorrect Monitor Scope | `#412` |
| Invariant Too Strong | `#413` |

G4 verification critics and G5 trace critics cite these IDs when a counterexample classification applies.

### 1. Missing guard

**Symptom**: the counterexample reaches an action without a required precondition being true.

**Trace signature**: a variable the assertion depends on is never set to the expected value because the action fired without the necessary `require` guard.

```
Step 1: stream.send         <-- fires without connection being established
  connected = false         <-- should be guarded: require connected(the_cid)
```

**Root cause**: a `before` block is missing a `require` statement, or the `require` does not cover all necessary preconditions.

**Fix**: add the missing `require` to the `before` block.

```ivy
before stream.send(id:stream_id, data:stream_data) {
    require connected(the_cid);            # Add missing guard
    require stream_state(id) = open;       # Add missing guard
}
```

### 2. Uninitialized state

**Symptom**: a state variable has an unexpected value in Step 1 (the very first step), before any action has modified it.

**Trace signature**: a relation or function has an arbitrary value because no `after init` block sets it.

```
Step 1: packet_event
  conn_state = closed       <-- expected: should be initialized to 'idle'
```

**Root cause**: the specification does not include an `after init` block for this state variable, so Ivy treats it as unconstrained (any value is possible).

**Fix**: add initialization.

```ivy
after init {
    conn_state(C) := idle;           # Initialize for all connection IDs
    conn_seen(C) := false;           # Initialize boolean relation
}
```

### 3. Incorrect monitor scope

**Symptom**: a monitor triggers on the wrong action, or a `before` / `after` block is attached to the wrong event.

**Trace signature**: the counterexample shows an action firing that should have been constrained, but the constraint is on a *different* action.

```
Step 1: frame.rst_stream.handle     <-- this action is unconstrained
  stream_state = open                <-- violation: should require stream_state = sending
```

Meanwhile, the `require` guard exists but is attached to `frame.stream.handle` instead of `frame.rst_stream.handle`.

**Root cause**: the `before` / `after` monitor watches the wrong action, or uses the wrong `mixin_kind` (e.g., `before` when `after` is needed for state-update checks).

**Fix**: move or duplicate the constraint to the correct action.

```ivy
before frame.rst_stream.handle(f:frame.rst_stream, scid:cid, dcid:cid) {
    require stream_state(f.id) = sending;    # Guard on the correct action
}
```

### 4. Invariant too strong

**Symptom**: the invariant asserts something that is temporarily false during a legitimate state transition, and the counterexample catches the transient state.

**Trace signature**: the state is correct at the start and end of a multi-step sequence, but the invariant fires during an intermediate step.

```
Step 1: connection.open
  handshake_done = false       <-- invariant: require handshake_done -> data_sent
  data_sent = false            <-- OK: both false, implication holds

Step 2: connection.handshake_complete
  handshake_done = true  (was: false)
  data_sent = false            <-- VIOLATION: handshake_done is true but data_sent is still false
```

**Root cause**: the invariant `handshake_done -> data_sent` is too strong — it does not account for the state between handshake completion and the first data send.

**Fix options**:

- **Weaken the invariant**: `handshake_done & ~in_handshake_transition -> data_sent`.
- **Restructure**: move the check to `_finalize` instead of an invariant, so it only checks end-state.
- **Add intermediate state**: introduce a guard variable that tracks the transition phase.

## Fix strategies

| Pattern | Fix |
|---------|-----|
| Action fires in invalid state | Add `require` guards to `before` block; use `ivy_coverage(mode="gaps")` for related gaps |
| Unexpected initial value | Add `after init` block initializing all relations / functions used by the assertion |
| Monitor on wrong action | Move / duplicate constraint to the action that actually fires in the trace |
| Invariant catches transient state | Weaken to exclude transition phase, or move check to `_finalize` |

## Lifecycle placement

| Check Type | Where to Place |
|---|---|
| Preconditions | `before` block with `require` |
| State updates | `after` block with assignment |
| Compliance checks | `after` block with `require` |
| End-state properties | `_finalize` action |
| Always-true properties | `invariant` (use sparingly) |

## Worked example

Load `trace-example.md` (sibling reference file) for a complete end-to-end trace interpretation example.
