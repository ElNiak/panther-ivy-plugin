# Refine-ops — failure-diagnosis reference

Detailed failure-diagnosis and fix procedures for refine-ops Phases 6 and 7, plus the G4 verification-gate discipline contract dispatched inline after every `ivy_verify` return.

---

## G4 verification gate

Dispatched inline by the verifier agent after every `ivy_verify` return (pass or fail). A PostToolUse hook also fires as a backstop, but the inline dispatch is what the workflow consumes for its verdict.

### Trigger and catalog slice

- **Trigger**: every `ivy_verify` return, dispatched from Phase 4 in the same turn.
- **Catalog slices applied by critics**: `#200-249` (structural patterns) + `#250-299` (layer-modeling patterns) + `#400-499` (verification-soundness patterns).

### What the critics audit

The load-bearing purpose is to catch **false `SOUND`** — `ivy_verify` returning `status: OK` when the proof obligation collapsed for a non-soundness reason. Specifically the critics scan for:

| Pattern | Meaning |
|---|---|
| `#403` | Error whitelisted via comment-out or `assume` |
| `#401` | Unsound `assume` collapsed the proof obligation |
| `#402`, `#207` | Trusted-isolate NativeAction leak into other isolates |
| `#404` | Solver wall-timeout masquerading as pass (`duration_s` near `timeout`) |

### Verdict handling

- **`VERDICT_SOUND`** — treat `ivy_verify` result as authoritative; advance the workflow.
- **`VERDICT_UNSOUND`** — write `[GAP: #NN]` markers at the cited sites. These must be resolved (fix and re-verify) or deliberately promoted to `// DEFERRED YYYY-MM-DD: …` before the workflow treats the verification as conclusive.
- **`VERDICT_ABSTAIN`** — treat the verdict as inconclusive — not a pass, not a fail. Proceed to Phase 6 Diagnose using the `abstain_reason` as the starting hypothesis; do not accept the upstream `ivy_verify` result without a concluding verdict from a subsequent G4 run.

### Discipline contracts

Verbatim prompts, dual-context isolation, asymmetric-vote rule, and pigeonhole exit live in the gate-critic catalog under `references/gates.md` and `references/critic_prompts/g4_verification.md`. GAP-marker conventions (placement per file type, promotion rules, anti-patterns): `.claude/rules/gap-markers.md`. Dispatch shape: the multi-Agent single-message dispatch pattern (`Skill(skill="panther-ivy-plugin:ivy")` then `references/parallel-dispatch.md`).

---

## Phase 6 — Diagnose

### Step 1: Load failure-pattern catalog (inline)

Invoke `Skill(skill="panther-ivy-plugin:verification-failures")` to load the numbered counterexample-pattern index, debugging methodology, and the claim-resolution gate. The verifier agent owns counterexample interpretation in-place — there is no separate diagnostic-agent dispatch for pattern-based diagnosis. The catalog is the agent's reference; this loop step is a guarded reload, not a sub-agent call.

### Step 2: Walk the counterexample

For each step in the `counterexample.steps` array:

1. Identify the firing action and the variable assignments.
2. Match the step against catalog patterns (e.g., `#410` missing-guard, `#420` invariant-induction-gap, `#430` array-bounds-state-coupling).
3. Cite the catalog pattern by number when summarizing the diagnosis. Pattern numbers come from the `verification-failures` catalog verbatim; do not coin local numbers.

### Step 3: MPE diagnosis (when patterns disagree)

When multiple catalog patterns plausibly explain the trace, or when the trace does not cleanly match any single pattern, apply the **Multi-Perspective Exploration (MPE)** pattern. Dispatch 3 sibling `Explore` agents in parallel — single message, three `Agent` tool calls (`Skill(skill="panther-ivy-plugin:ivy")` `references/parallel-dispatch.md` for the canonical dispatch shape):

- **Exploration question:** "What is the root cause of this verification failure and what is the best fix strategy?"
- **Agents (all 3 in parallel):**
  - **Conservative Architect** (`subagent_type: "Explore"`) — top-down design analysis: layer structure, missing abstractions, assume-guarantee contracts.
  - **Pragmatic Engineer** (`subagent_type: "Explore"`) — state-machine walk-through: which transition allows the bad reachable state.
  - **Adversarial Auditor** (`subagent_type: "Explore"`) — alternative-input stress test: are there other inputs that would trigger the same failure? Symptom or deeper problem?

Aggregate the three findings before classifying.

### Step 4: Classify the failure

Classify into one of three categories:

- **Invariant violation** — a property that should hold does not. The counterexample trace shows a reachable state where an invariant or `require` is falsified.
- **Type error** — type mismatch, missing type interpretation, or unresolved type in the model.
- **Structural issue** — include path problems, missing modules, circular dependencies, unresolved symbols.

On structural issues, dispatch the `model-reviewer` agent for a deeper audit of the model's include graph and layer structure. This is the only Phase 6 sub-agent dispatch besides MPE — pattern-based diagnosis stays inline.

### Step 5: Present diagnosis

Report to the user with the failure classification, the cited catalog patterns, and (if MPE was run) the aggregated finding from the three Explore agents.

### Gate checkpoint

Ask via `AskUserQuestion`: "Fix it yourself, or want me to attempt the fix?" Wait for explicit confirmation before proceeding.

### Step 6: Update state

Update phase to `"diagnosed"` via `ivy_workflow_state(action="set", workflow="verify", phase="diagnosed", protocol="<protocol>")`.

---

## Phase 7 — Fix

Only entered if the user accepts the auto-fix offer from Phase 6.

### Situation Briefing — Fix Strategy

Apply the **Situation Briefing** pattern (a structured pre-action context dump):

- **What happened:** Summarize the diagnosis: failure classification, root cause hypothesis, and the cited catalog pattern.
- **Options via `AskUserQuestion`:**
  - "Apply the recommended fix from the diagnosis" (describe the specific fix)
  - "Try a different fix approach" (if MPE roles disagreed, present the alternative)
  - "Fix it manually — I'll handle this"
  - "Abandon this test and move on"

### Step 1: Attempt-counter gate

Before applying the fix, evaluate the attempt-counter gate:

1. Compute the attempt key as the test file path relative to the protocol directory.
2. Read the journal (`ivy_workflow_state(action="get_journal", last_n=200)`), walk backward to the most recent `decision{kind: "override_attempt_cap", key: <same>}` entry (`override_idx`), then count `progress{kind: "fix_attempt", key: <same>}` entries after `override_idx`.
3. If `count >= 3`, DO NOT apply the fix. Present via `AskUserQuestion` the 3-option escalation menu:
   - **Continue anyway** — record an `override_attempt_cap` decision and reset the cap.
   - **Abandon this file** — record a decision and exit to On Completion.
   - **Switch workflow** — emit `pending_dispatch(build, ...)` for structural rethink.
4. Otherwise, append the fix-attempt marker and proceed:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="progress",
     state='{"kind": "fix_attempt", "key": "<test_file>", "attempt": <int>}'
   )
   ```

The cap is 3 attempts per test file, cumulative across sessions until an `override_attempt_cap` decision soft-resets the count. Raise the cap only via the journal-visible decision event.

### Step 2: Apply the fix

Apply the fix indicated by the inline counterexample interpretation. If editing `.ivy` files, invoke `Skill(skill="panther-ivy-plugin:ivy-syntax")` to load language reference guidance before making changes. After the Edit, follow the post-Edit workspace-block recovery pattern documented in `references/workspace-block-recovery.md`.

### Step 3: Re-verify

Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) → Phase 4 (execute) → Phase 6 (diagnose) → Phase 7 (fix) → Phase 3 again.

This loop continues until verification passes, the user decides to stop, or the journal-counted attempt cap fires (3 attempts per test file, cumulative across sessions; soft-reset via the `override_attempt_cap` decision event).

### On user stopping

Update phase to `"stopped"` and proceed to completion.

### Knowledge Gate: post-fix

**Knowledge Gate.** Pause for the G6 knowledge-capture vote — the orchestrator dispatches `g-knowledge-critic` ×3 in parallel (asymmetric vote) on whether session learnings are worth persisting (rules, references, feedback memory).

- Reflect on the bug that was diagnosed and fixed — what was non-obvious?
- Capture the error-to-fix pattern for future sessions.
- Save session log (observability events + digest).
- If candidates found, classify and present for user confirmation.
- Resume workflow after the vote completes.

---

## Post-IUT wire validation

After an IUT test completes (regardless of verdict), cross-validate the Ivy event log against the pcap capture to detect cases where the model passed but the test did not effectively exercise the IUT.

### When to run

Run wire validation after every `ivy_iut_test` invocation that returns a PASS verdict. A PASS with insufficient wire traffic is a false positive: the model's safety properties held vacuously because the generator never produced meaningful protocol messages.

### Step 1: Extract pcap message counts per direction

Use tshark to count protocol messages sent by the Ivy tester and by the IUT:

```bash
# Messages sent by Ivy (tester -> IUT)
tshark -r <pcap> -Y "bgp && ip.src==<ivy_ip>" -T fields -e bgp.type | sort | uniq -c

# Messages sent by IUT (IUT -> tester)
tshark -r <pcap> -Y "bgp && ip.dst==<ivy_ip>" -T fields -e bgp.type | sort | uniq -c
```

Replace `bgp` with the appropriate protocol filter (e.g., `quic` for QUIC tests). Replace `<ivy_ip>` with the Ivy tester's IP address from the experiment config.

### Step 2: Compare pcap counts against iteration count

The test's `iterations_per_test` parameter sets how many random actions the generator attempts. A healthy test produces protocol messages proportional to the iteration count:

- **Expected**: At least 1 protocol message per 10-50 iterations (varies by protocol complexity)
- **Warning threshold**: Fewer than 1 message per 100 iterations
- **Failure threshold**: Fewer than 5 total protocol messages across all iterations

If message counts fall below the warning threshold, the generator is likely starved (see `verification-failures` for root causes).

### Step 3: Compare pcap message types against Ivy log event types

Extract the set of message types from the Ivy event log and from the pcap. They should be consistent:

- Every message type logged in Ivy events should appear in the pcap (serialization succeeded)
- Every protocol message in the pcap should correspond to an Ivy event (no unmodeled traffic)
- Message counts per type should roughly match (accounting for retransmissions)

### Step 4: Flag discrepancies

Report as **wire validation failure** if any of the following hold:

1. Pcap contains fewer than 5 protocol messages despite a high iteration count
2. Ivy log shows message events that do not appear in the pcap (serialization or shim failure)
3. Pcap contains message types not present in the Ivy event log (unmodeled IUT behavior)
4. IUT hold timer expires or connection drops before the test completes (insufficient keepalive generation)

A wire validation failure does not invalidate the formal verification result but indicates the IUT was not effectively tested. The test should be re-run after fixing the generator (see `verification-failures` for the generator-starvation entry).

### Step 5: Record in test report

Include wire validation results in the test report alongside the formal verdict:

```
Verdict: PASS
Wire validation: WARN (3 BGP messages in 1000 iterations)
  - OPEN: 1 sent, 1 received
  - KEEPALIVE: 2 sent, 0 received
  - UPDATE: 0 sent, 0 received
Recommendation: Generator starvation detected. Review exported actions and timer competition.
```
