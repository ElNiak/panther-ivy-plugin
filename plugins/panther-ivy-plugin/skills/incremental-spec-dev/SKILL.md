---
name: incremental-spec-dev
description: Use when adding requirements to an Ivy specification one at a time with verification between each addition. Guides the add-verify-iterate loop for incremental formal specification development.
---

# Incremental Specification Development

This skill guides the iterative loop for adding RFC requirements to an Ivy formal specification one at a time. Each iteration adds exactly one requirement, verifies the model, and tracks coverage progress before moving to the next.

---

## The Incremental Loop

Each requirement follows this 9-step cycle. Never skip steps or batch multiple requirements.

### Step 1: Identify the Next RFC Requirement

Use `ivy_coverage(mode="gaps")` to find uncovered MUST requirements first, then SHOULD:

```
ivy_coverage(mode="gaps", protocol="{prot}")
```

This returns `unguarded_state_vars`, `uncovered_requirements`, and `orphaned_monitors`. Focus on `uncovered_requirements` entries tagged with MUST level.

### Step 2: Choose the Formal Model Pattern

Use `ivy_patterns(mode="analyze")` to determine which pattern applies to the requirement:

```
ivy_patterns(mode="analyze", protocol="{prot}")
```

Common patterns and when they apply:

| Requirement Type | Pattern | Placement |
|---|---|---|
| Precondition on sending | **Monitor** (before) | `{prot}_{role}_behavior.ivy` |
| Postcondition after receiving | **Monitor** (after) | `{prot}_{role}_behavior.ivy` |
| State transition constraint | **State machine** | `{prot}_connection.ivy` or behavior file |
| Data format validation | **Variants** | `{prot}_frame.ivy` or `{prot}_packet.ivy` |
| End-state property | **_finalize** | Test specification file |

### Step 3: Write the Bracket-Tag Annotation and Monitor/Assertion

Add the requirement to the appropriate `.ivy` file:

```ivy
# Before: guard precondition
before frame.stream.handle(f:frame.stream, scid:cid, dcid:cid, e:quic_packet_type) {
    require f.offset + f.length <= max_stream_data(f.stream_id);  # [rfc9000:4.1]
}

# After: state update + compliance check
after packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {
    require pkt.hdr.version = negotiated_version;  # [rfc9000:6.2]
}
```

Rules for writing the assertion:
- **RFC bracket-tag format**: `# [rfc9000:X.Y]` as a trailing comment on the `require`/`ensure` line
- **Monitor placement**: `before` for preconditions (what must hold before an event), `after` for postconditions (what must hold after)
- **State variable guards**: `require var_name(args)` for safety properties that depend on protocol state
- **Refer to the ivy-writing-guide skill** for full Ivy syntax details

### Step 4: Fast Check with `ivy_lint`

Run structural validation (completes in milliseconds):

```
ivy_lint(relative_path="{path_to_modified_file}")
```

This catches:
- Missing `#lang ivy1.7` header
- Unresolved include references
- Unmatched braces and syntax errors
- Structural problems that would waste minutes in full verification

**Fix any lint errors before proceeding.** Do not skip this step.

### Step 5: Formal Check with `ivy_verify`

Run full formal verification:

```
ivy_verify(relative_path="{path_to_modified_file}")
```

If verification succeeds, proceed to Step 7.

### Step 6: If Verification Fails -- Diagnose and Fix

When `ivy_verify` returns a failure:

1. Read the `counterexample_trace` field in the output for a human-readable state trace
2. Use the **counterexample-guide** skill for structured interpretation of the failure
3. Common failure causes and fixes:

| Failure | Likely Cause | Fix |
|---|---|---|
| Invariant not preserved | New assertion conflicts with existing state | Add a strengthening invariant or narrow the assertion scope |
| Safety property violated | Unreachable state is now reachable | Add a `require` guard in a `before` block |
| Ungrounded variable | Free variable in assertion | Bind the variable: `require P = the_cid -> property(P)` |
| Z3 timeout | Proof obligation too complex | Break into smaller isolates, add auxiliary lemmas |

4. After fixing, return to Step 4 (lint) and Step 5 (verify) again. Do not proceed until verification passes.

### Step 7: Track Coverage Progress

Run coverage statistics to confirm the requirement is now covered:

```
ivy_coverage(mode="stats", protocol="{prot}")
```

Compare `covered` and `coverage_percent` with the previous iteration. The newly added requirement should appear as covered.

### Step 8: Quality Gate Check

Run the quality gate after each addition:

```
ivy_quality(mode="gate", protocol="{prot}", level="minimal")
```

Gate levels:
- **minimal**: Basic structural and verification checks -- use during iteration
- **standard**: Adds test specification and monitor checks -- use at milestone points
- **comprehensive**: Full manifest and coverage audit -- use before finalizing

If the gate fails, address the reported issues before continuing.

### Step 9: Commit the Working Requirement

Commit the single requirement addition with a message referencing the RFC section:

```
git add {modified_files}
git commit -m "spec({prot}): add [rfcNNNN:X.Y] requirement - {brief description}"
```

One commit per requirement keeps the git history bisectable and each commit independently verifiable.

---

## Picking the Next Requirement

### Priority Order

1. **MUST** requirements first -- these are absolute protocol requirements and form the safety-critical core
2. **SHOULD** requirements second -- recommended behavior that strengthens the model
3. **MAY** requirements last -- optional behavior, test correct handling when present

### Selection Strategy

- **Start with minimal dependencies**: Pick requirements that depend on the fewest other state variables. A requirement like "packets MUST include a version field" is simpler than "the handshake MUST complete before application data."
- **Group related requirements**: Work through requirements from the same RFC section or that share state variables. For example, all stream flow control requirements (RFC 9000 Section 4) share `max_stream_data` and `total_data_sent`.
- **Build state incrementally**: Add state variables (relations, functions) as needed by each requirement. Do not pre-declare state variables you are not yet using.

### Finding Uncovered Requirements

Use `ivy_extract_requirements` to parse remaining uncovered RFC sections:

```
ivy_extract_requirements(relative_path="{rfc_text_file}", output="structured")
```

This returns normative statements (MUST/SHOULD/MAY) with section references. Cross-reference against `ivy_coverage(mode="gaps")` to identify which ones still need assertions.

For a full traceability view:

```
ivy_coverage(mode="matrix", protocol="{prot}")
```

This shows the requirement-to-annotation mapping, making it clear which RFC sections have no corresponding Ivy assertions.

---

## Writing the Assertion

### RFC Bracket-Tag Format

Every `require`, `ensure`, `assume`, or `assert` must include a bracket tag:

```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
ensure stream_data_delivered;               # [rfc9000:2.2]
```

Use multi-tags (`[rfc9000:14.1, rfc9000:8.1]`) only when a single assertion genuinely covers multiple requirements.

### Monitor Placement

| Placement | Purpose | Example |
|---|---|---|
| `before action(...)` | Precondition guard -- what must hold before the event | `require connected(the_cid);` |
| `after action(...)` | Postcondition check + state update -- what must hold after | `require pkt.version = negotiated_version;` |
| `around action(...)` | Combined pre/post with access to both old and new state | Serialization dispatch logic |

### State Variable Guards

For safety properties that depend on protocol state, use explicit guards:

```ivy
before frame.stream.handle(f) {
    if _generating {
        require connected(the_cid);                    # Guard: only when connected
        require f.stream_id <= max_stream_id(the_cid); # [rfc9000:4.6]
    }
}
```

The `if _generating` guard ensures the constraint only applies to test traffic generation (Ivy-side), not to received traffic from the IUT.

---

## When to Stop Iterating

The incremental loop ends when all three conditions are met:

1. **All MUST requirements covered**: Verify with `ivy_coverage(mode="stats")` -- the `by_level.MUST.coverage_percent` should be 100%.
2. **Quality gate passes at target level**: Run `ivy_quality(mode="gate", level="standard")` (or `comprehensive` for release-quality specifications). All checks must pass.
3. **No verification failures**: The current specification passes `ivy_verify` cleanly with no counterexamples and no Z3 timeouts.

After MUST requirements are complete, repeat the loop for SHOULD requirements if time permits. MAY requirements are lowest priority and may be deferred.

---

## Anti-Patterns to Avoid

### 1. Adding Multiple Requirements Without Verifying Between Each

**Wrong**: Write five monitors, then run `ivy_verify` once.

**Right**: Write one monitor, lint, verify, track coverage, commit. Then the next.

**Why**: When verification fails after adding five requirements, you cannot tell which one caused the failure. The incremental approach gives immediate feedback and keeps the specification in a known-good state at every commit.

### 2. Skipping `ivy_lint`

**Wrong**: Go straight to `ivy_verify` after editing.

**Right**: Always run `ivy_lint` first.

**Why**: `ivy_lint` runs in milliseconds and catches structural errors (missing header, unresolved includes, syntax). `ivy_verify` takes seconds to minutes. Catching a typo in 50ms instead of 120 seconds compounds across dozens of iterations.

### 3. Ignoring Coverage Gaps in State Variable Guards

**Wrong**: Write `require property(X)` without checking that the state variable `property` is properly initialized and guarded.

**Right**: Check with `ivy_coverage(mode="gaps")` that state variables have initialization (`after init` blocks) and guard conditions in all relevant `before` blocks.

**Why**: Uninitialized state variables start with arbitrary values in Ivy. A `require conn_seen(C)` without `after init { conn_seen(C) := false }` will have unpredictable behavior. The gaps tool identifies unguarded state variables explicitly.

### 4. Committing Without a Passing Quality Gate

**Wrong**: Commit after `ivy_verify` passes but without checking the quality gate.

**Right**: Run `ivy_quality(mode="gate", level="minimal")` after each addition.

**Why**: Verification passing means the model is internally consistent, but it does not check naming conventions, missing bracket tags, or traceability. The quality gate catches these.

### 5. Pre-declaring State Variables Not Yet Needed

**Wrong**: Add 20 relations and functions at the start "in case we need them."

**Right**: Add state variables as each requirement demands them.

**Why**: Unused state variables inflate the verification state space, slow down Z3, and create false gaps in coverage reports. Add what you need, when you need it.

---

## Integration

**Related skills:**
- **counterexample-guide** -- Interpreting verification failures from Step 6
- **ivy-writing-guide** -- Ivy language syntax for writing assertions (Step 3)
- **specification-patterns** -- 14-layer template and formal model patterns (Step 2)
- **workflow-reference** -- RFC-to-Ivy mapping patterns and quality gate details
- **tooling-reference** -- MCP tool parameter reference for all tools used in this workflow

**Related agents:**
- **spec-analyst** -- Automated verification and diagnosis
- **traceability-agent** -- Coverage review and gap analysis
