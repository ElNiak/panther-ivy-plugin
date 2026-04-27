---
name: knowledge-verification-failures
description: "Use when ivy_verify FAIL, ivy_check failed, counterexample appears, or an adversarial gate cites pattern #NN. Owns numbered verifier-pattern catalog, debugging methodology, counterexample interpretation, and claim-resolution gate."
user-invocable: false
---

# Verification-Failure Knowledge

**Type:** flexible — adapt principles to context.

This skill consolidates four lifecycle-related knowledge surfaces invoked
when verification produces signal: error-pattern lookup, the mandatory
pre-fix debugging methodology, structured counterexample interpretation,
and the claim-resolution gate that records the outcome inline. Use the
section that matches your trigger.

| Trigger | Section |
|---|---|
| Cryptic Ivy compile/verify error string (`'X' not found`, `ungrounded`, `invariant failed`, `type mismatch`); adversarial gate cites catalog `#NN` | [Error-pattern catalog](#error-pattern-catalog) |
| `ivy_verify` / `ivy_check` failed and a fix is being prepared | [Debugging methodology](#debugging-methodology) |
| `ivy_verify` output contains `counterexample` or `counterexample_trace` | [Counterexample interpretation](#counterexample-interpretation) |
| `ivy_verify` FAIL, `ivy_coverage` shows gaps, or `model-reviewer` reports issues that need an inline resolution comment | [Claim-discussion gate](#claim-discussion-gate) |

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

---

## Error-pattern catalog

This section owns three reference files:

- **`references/verifier_patterns.md`** — the numbered, append-only catalog cited by adversarial quality gates G1–G5. Each entry carries a sparse ID preserving source provenance, a trigger condition, a check procedure, a source citation, and a methodology tag (`NCT` | `NACT` | `NSCT` | `Ivy` | `Plugin-Memory`).
- **`references/error-table.md`** — the legacy quick-lookup table for cryptic Ivy error messages, kept for fast-path debugging.
- **`references/generator-patterns.md`** — pattern guide for Ivy test-traffic generators; anti-patterns (timer competition, two-step message construction, missing handle exports, over-constrained guards) and the correct patterns (auto-send, handle exports).

### How to use

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

### Top 5 most common errors (quick reference)

| Error Substring | Root Cause | Fix |
|---|---|---|
| `'X' not found` | Parameter name collides with existing symbol | Use single uppercase letter params (`S:type`, `D:type`) |
| `ungrounded variable` | Free variable not bound by quantifier | Add explicit quantifier or ensure var appears in head |
| `invariant ... failed` | Action violates declared invariant | Add `require` guard, fix `after init`, or weaken invariant |
| `assumption failed` | Isolate assumption not satisfied by spec | Run `ivy_model_info`, check assumed isolate's guarantees |
| Missing `after init` | Relations start with arbitrary values | Add `after init { rel(X) := false; }` block |

### Catalog overview

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

---

## Debugging methodology

### Hard rule

The checklist below is mandatory because fixes proposed without evidence from it are flagged UNSOUND by the G4 verification gate. If no working example or skill reference explains the error, say so explicitly rather than guessing.

### Mandatory pre-fix checklist

#### Step 1: Parse the error

Extract from the error output:
- **Error type** (the key phrase: `not found`, `invariant failed`, `type mismatch`, etc.)
- **Line number** and **file path**
- **Symbol or construct** that failed

#### Step 2: Diagnostic interpretation protocol

If the error came from `ivy_verify`, `ivy_diagnostics`, or LSP diagnostics, read the **full `diagnostics` array**, not just `error_summary`.

Classify each diagnostic by its `source` field:

| Source | Layer | What It Means |
|--------|-------|---------------|
| `"ivy"` | Parser | Syntax or parse error in the Ivy file |
| `"ivy-lint"` | Structural | Fast structural check (braces, headers, includes) |
| `"ivy-lsp"` | LSP analysis | In-process semantic check (collisions, missing init) |
| `"ivy-lsp-reqs"` | Requirements | Requirement coverage gap |
| `"ivy-lsp-semantic"` | RFC tags | Orphaned or missing bracket tags |
| `"ivy-lsp-coverage"` | Coverage | Unmonitored actions or unguarded state |
| `"ivy_check"` | Verification | Full formal verification result |

**Priority cascade:** Fix Error-severity diagnostics first. Then Warning. Then Info/Hint.

When a diagnostic points to a specific line, read 5 lines above and below before forming a hypothesis.

#### Step 3: Consult skills

Load and check these skills for the failing construct:
- This skill's [Error-pattern catalog](#error-pattern-catalog) section — look up the specific error message substring
- `knowledge-ivy-writing-guide` — check syntax rules for the construct type (relation, function, action, invariant, etc.)

#### Step 4: Run structural check

Call `ivy_diagnostics` in structural mode before full verification. It runs in milliseconds and catches structural issues (missing `#lang`, unmatched braces, unresolved includes, parameter name collisions, missing `init`) without the cost of `ivy_verify`. Canonical invocation shape: load `Skill(skill="panther-ivy-plugin:knowledge-ivy-toolkit")` and consult `references/tool-invocation-examples.md`.

#### Step 5: Search existing models for working examples

Use `Grep` to find similar constructs in `protocol-testing/`:

- For `relation` issues: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/")`
- For `function` issues: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/")`
- For `after init` issues: `Grep(pattern="after init", glob="*.ivy", path="protocol-testing/")`
- For `invariant` issues: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/")`
- For `action` issues: `Grep(pattern="^action |^    action ", glob="*.ivy", path="protocol-testing/")`

**Prioritize models for the same protocol family** (e.g., when debugging BGP, search `protocol-testing/bgp/` first).

#### Step 6: Formulate theory

Before editing anything, state a specific hypothesis:
- "The error `'src' not found` occurs because Ivy resolves parameter names as symbols. Existing QUIC models use single uppercase letters (C, S, P). The fix is to rename `src` to `S`."

The theory MUST reference evidence from steps 2-5. If you have no evidence, say so.

#### Step 7: Apply minimal fix

Only now propose a change. Make it minimal — change only what's needed to fix the specific error.

#### Step 8: Verify

Run verification to confirm the fix. For the canonical invocation shape, load the ivy-toolkit skill via `Skill(skill="panther-ivy-plugin:knowledge-ivy-toolkit")` and consult its tool-invocation-examples reference. If the fix introduces new errors, return to Step 1 for the new error.

### Serializer/deserializer debugging

For C++ serializer state machine issues (wrong bytes on wire, `deser_err` throws, state machine stuck), load the `knowledge-ivy-writing-guide` skill and read `references/serializer-patterns.md`.

### Self-evaluation reference

`references/debugging-environment.md` — self-evaluation protocol (anti-pattern checklist), debug environment variables, LSP indexing awareness. For the full 9-step health-check runbook (log paths, common failures, process liveness), dispatch the triage skill via `Skill(skill="panther-ivy-plugin:workflow-triage")`.

---

## Counterexample interpretation

When `ivy_verify` returns a verification failure, it may include structured counterexample data showing exactly how the property was violated. This section provides a systematic workflow for reading counterexample traces, diagnosing the root cause, and applying the correct fix.

### When this section applies

Use this section when `ivy_verify` output contains either:

- **`counterexample`**: Structured dict with `assertion`, `assertion_line`, and `steps` (parsed from raw ivy_check output)
- **`counterexample_trace`**: Human-readable formatted trace with step-by-step state changes

If verification fails but no counterexample is present, the failure is likely a type error, unresolved symbol, or Z3 timeout — load the `knowledge-methodology-reference` skill instead.

**Methodology note.** Under NCT the default interpretation of a counterexample is *the IUT-side spec violates a compliance invariant*. Under NACT the perspective flips: a counterexample typically means *the attacker cannot reach a state the attack model claims is reachable* (i.e. the attack model is over-constrained). Under NSCT, counterexamples also need to be weighed against the seed / replay context (see `knowledge-methodology-reference` for the per-methodology interpretation decision tree).

### Interpretation workflow

#### Step 1: Read the violated assertion

Look at the `counterexample_trace` field first. The header tells you what failed:

```
Violated assertion (Line 42):
  require conn_seen(C)
```

This gives you:
- **Line number**: Where the failing `require`/`assert`/`ensure` lives
- **Assertion text**: The property that the solver proved can be violated

Use `Read` to view the assertion in context (surrounding before/after block, action signature).

#### Step 2: Identify the execution trace

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

#### Step 3: Trace state variable changes

Walk through the steps and look for:
1. **Variables that never change when they should** — e.g., `conn_seen` stays `false` across all steps, but the assertion expects it to be `true` after `quic_connection.open`
2. **Variables that change unexpectedly** — marked with `(was: X)`, indicating a state transition happened
3. **Missing steps** — if you expect an intermediate action (like a handshake) but it does not appear, a guard may be too permissive

#### Step 4: Look up the violated symbol

Use `ivy_model_info` to understand the symbol's definition, or `Grep` to find its declaration across include files.

#### Step 5: View state machine context

```
ivy_visualize(view="state_machine", test_file="path/to/test.ivy")
```

This shows all states and transitions, helping you spot whether the counterexample trace represents a valid but unguarded path through the state machine.

#### Step 6: Check related coverage

```
ivy_coverage(mode="gaps", test_file="path/to/test.ivy")
```

Look for unguarded state variables or orphaned monitors that relate to the failing assertion. The counterexample often exploits a gap that this tool can identify.

### Common failure patterns

Each of the four patterns below is catalogued (with IDs `#410`–`#413`) in `references/verifier_patterns.md` for adversarial-gate citation:

| Pattern here | Catalog ID |
|---|---|
| Missing Guard | `#410` |
| Uninitialized State | `#411` |
| Incorrect Monitor Scope | `#412` |
| Invariant Too Strong | `#413` |

G4 verification critics and G5 trace critics cite these IDs when a counterexample classification applies.

#### 1. Missing guard

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

#### 2. Uninitialized state

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

#### 3. Incorrect monitor scope

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

#### 4. Invariant too strong

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

**Root cause**: The invariant `handshake_done -> data_sent` is too strong — it does not account for the state between handshake completion and the first data send.

**Fix options**:
- **Weaken the invariant**: `handshake_done & ~in_handshake_transition -> data_sent`
- **Restructure**: Move the check to `_finalize` instead of an invariant, so it only checks end-state
- **Add intermediate state**: Introduce a guard variable that tracks the transition phase

### Fix strategies

| Pattern | Fix |
|---------|-----|
| Action fires in invalid state | Add `require` guards to `before` block; use `ivy_coverage(mode="gaps")` for related gaps |
| Unexpected initial value | Add `after init` block initializing all relations/functions used by the assertion |
| Monitor on wrong action | Move/duplicate constraint to the action that actually fires in the trace |
| Invariant catches transient state | Weaken to exclude transition phase, or move check to `_finalize` |

### Lifecycle placement

| Check Type | Where to Place |
|---|---|
| Preconditions | `before` block with `require` |
| State updates | `after` block with assignment |
| Compliance checks | `after` block with `require` |
| End-state properties | `_finalize` action |
| Always-true properties | `invariant` (use sparingly) |

### Worked example

Load `references/trace-example.md` for a complete end-to-end trace interpretation example.

---

## Claim-discussion gate

Structured discussion templates for resolving verification claims, RFC mapping decisions, and coverage gap priorities. Select the template matching your trigger.

### Template selection

| Trigger | Template |
|---------|----------|
| `ivy_verify` FAIL or model-reviewer ERROR | `references/verification-claim.md` |
| `ivy_extract_requirements` or RFC mapping | `references/mapping-claim.md` |
| `ivy_coverage(mode="gaps")` shows uncovered reqs | `references/coverage-claim.md` |

After identifying the matching trigger above, load the corresponding file: `references/verification-claim.md`, `references/mapping-claim.md`, or `references/coverage-claim.md`.

### Persistence — inline resolution comments

All claim discussion outcomes are recorded as inline comments in the source file. The date is always in ISO format (`YYYY-MM-DD`) and the comment prefix matches the host file's syntax: `#` for `.ivy`, `#` for `.yaml`, `<!-- … -->` for `.md`. This parallels the `[GAP: …]` placement rules in `.claude/rules/gap-markers.md`; a resolution comment is the author-written successor to a gate-written GAP marker.

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

#### Rules

- Keep comments concise (one line)
- Place on the same line as the assertion when possible
- Never remove existing resolution comments — append if revisiting

---

## Integration

- **Loaded by:** `workflow-verify` (Phase 6 Diagnose), `workflow-build` (Phase 3 on compile error), `workflow-review` (Phase 3 on contested findings); G4 verification critics, G5 trace-analysis critics, and the `model-reviewer` / `spec-analyst` agents during their dispatch phases.
- **Precedes:** the G4 verification gate cites the eight pre-fix steps under [Debugging methodology](#debugging-methodology) (catalog entry `#405`); fixes proposed without these steps are UNSOUND by gate criteria.

**Related skills:**

- `knowledge-ivy-writing-guide` — language reference consulted by the debugging methodology, the counterexample fix code, and the claim-discussion comments.
- `knowledge-ivy-toolkit` — MCP tool inventory consulted by structural-check and re-verify steps.
- `knowledge-methodology-reference` — verification cycle context and the per-methodology interpretation decision tree for counterexamples.
- `cross-cutting-reflection-patterns` — adversarial-gate discipline layer; G4 and G5 critic templates load this skill alongside the catalog above.

**Related agents:**

- `spec-analyst` — automated diagnosis (consumes the catalog and the debugging methodology).
- `model-reviewer` — adversarial review (consumes the catalog and the claim-discussion templates).

**MCP tools used:**

- `ivy_verify` — source of counterexamples.
- `ivy_diagnostics` — structural check and full diagnostic array.
- `ivy_model_info` — symbol look-up.
- `ivy_visualize(view="state_machine")` — state-transition view.
- `ivy_coverage(mode="gaps")` — coverage gap discovery.
- LSP `hover` / `findReferences` / `goToDefinition` — symbol look-up across includes.
