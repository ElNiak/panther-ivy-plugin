# Verify Workflow — Failure Diagnosis Reference

Detailed failure diagnosis and fix procedures for the verify workflow (Phases 6 and 7), plus the G4 verification-gate discipline contract fired PostToolUse on `ivy_verify`.

---

## G4 Verification Gate

Fires PostToolUse on every `ivy_verify` return (pass or fail). A PostToolUse hook spawns G4 verification critics from the `reflection-patterns` skill.

### Trigger and catalog slice

- **Hook**: PostToolUse on `ivy_verify`.
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

- **`VERDICT_SOUND`** → treat `ivy_verify` result as authoritative; advance the workflow.
- **`VERDICT_UNSOUND`** → the orchestrator writes `[GAP: #NN]` markers at the cited sites. These must be resolved (fix and re-verify) or deliberately promoted to `// DEFERRED YYYY-MM-DD: …` before the workflow treats the verification as conclusive.
- **`VERDICT_ABSTAIN`** → treat the verdict as inconclusive — not a pass, not a fail. Proceed to Phase 6 Diagnose using the abstain_reason as the starting hypothesis; do not accept the upstream `ivy_verify` result without a concluding verdict from a subsequent G4 run.

### Discipline contracts

Verbatim prompts, dual-context isolation, asymmetric-vote rule, pigeonhole exit: `reflection-patterns` skill, `references/gates.md` and `references/critic_prompts/g4_verification.md`. GAP-marker conventions (placement per file type, promotion rules, anti-patterns): `.claude/rules/gap-markers.md`.

---

## Phase 6 — Diagnose

### Step 1: Load failure interpretation guidance

Invoke the `counterexample-guide` skill to load trace interpretation guidance.

### Step 2: Multi-Perspective Diagnosis

Load the `reflection-patterns` skill. Apply **Pattern B (Multi-Perspective Exploration)**:

- **Exploration question:** "What is the root cause of this verification failure and what is the best fix strategy?"
- **Agents (dispatch all 3 in parallel):**
  - **spec-analyst** (use `subagent_type: "panther-ivy-plugin:spec-analyst"`): Analyze the failure trace with counterexample interpretation. Focus on which invariant/action is violated and why.
  - **Conservative Architect** (use `subagent_type: "Explore"`): Top-down analysis — check whether the failure indicates a design flaw in the layer structure, missing abstractions, or incorrect assume-guarantee contracts.
  - **Adversarial Auditor** (use `subagent_type: "Explore"`): Stress-test the current spec — are there other inputs that would trigger the same failure? Is this a symptom of a deeper problem?

Present the synthesized diagnosis before proceeding to classification.

### Step 3: Classify the failure

Classify into one of three categories:

- **Invariant violation** — a property that should hold does not. The counterexample trace shows a reachable state where an invariant or `require` is falsified.
- **Type error** — type mismatch, missing type interpretation, or unresolved type in the model.
- **Structural issue** — include path problems, missing modules, circular dependencies, unresolved symbols.

On structural issues, also dispatch the `model-reviewer` agent for a deeper audit of the model's include graph and layer structure.

### Step 4: Present diagnosis

Report to the user with the failure classification and the spec-analyst's diagnosis.

### Gate checkpoint

Ask the user: "Fix it yourself, or want me to attempt the fix?"

Wait for explicit confirmation before proceeding.

### Step 5: Update state

Update phase to `"diagnosed"` via `ivy_workflow_state(action="set", workflow="workflow-verify", phase="diagnosed", protocol="<protocol>")`.

---

## Phase 7 — Fix (optional)

Only entered if the user accepts the auto-fix offer from Phase 6.

### Situation Briefing — Fix Strategy

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)**:

- **What happened:** Summarize the diagnosis: failure classification, root cause hypothesis, and which agents agreed/disagreed.
- **Options:**
  - "Apply the [recommended fix] from the diagnosis" (describe the specific fix)
  - "Try a different fix approach" (if agents disagreed, present the alternative)
  - "Fix it manually — I'll handle this"
  - "Abandon this test and move on"

### Step 1: Apply the fix

Before applying the fix, evaluate the attempt-counter gate:

1. Compute the attempt key as the test file path relative to the protocol directory.
2. Read the journal (`ivy_workflow_state(action="get_journal", last_n=200)`), walk backward to the most recent `decision{kind: "override_attempt_cap", key: <same>}` entry (`override_idx`), then count `progress{kind: "fix_attempt", key: <same>}` entries after `override_idx`.
3. If `count >= 5`, DO NOT apply the fix. Present the 3-option escalation menu (`Continue anyway` records an `override_attempt_cap` decision and resets the cap; `Abandon this file` records a decision and exits to On Completion; `Switch workflow` emits `pending_dispatch(build, ...)` for structural rethink).
4. Otherwise, append the fix-attempt marker and proceed:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="progress",
     state='{"kind": "fix_attempt", "key": "<test_file>", "protocol": "<protocol>"}'
   )
   ```

Apply the fix suggested by the spec-analyst. If editing `.ivy` files, invoke the `ivy-writing-guide` skill to load language reference guidance before making changes. After the Edit, follow the post-Edit workspace-block recovery pattern documented in the main SKILL.md.

### Step 2: Re-verify

Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) → Phase 4 (execute) → Phase 6 (diagnose) → Phase 7 (fix) → Phase 3 again.

This loop continues until verification passes, the user decides to stop, or the journal-counted attempt cap fires (5 attempts per test file, cumulative across sessions; soft-reset via the `override_attempt_cap` decision event).

### On user stopping

Update phase to `"stopped"` and proceed to completion.

### Knowledge Gate: Post-Fix

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:cross-cutting-knowledge-capture")`
- Reflect on the bug that was diagnosed and fixed — what was non-obvious?
- Capture the error-to-fix pattern for future sessions
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Post-IUT Wire Validation

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

If message counts fall below the warning threshold, the generator is likely starved (see `generator-mechanics.md` for root causes).

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

A wire validation failure does not invalidate the formal verification result but indicates the IUT was not effectively tested. The test should be re-run after fixing the generator (see `ivy-error-patterns` skill, generator starvation entry).

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
