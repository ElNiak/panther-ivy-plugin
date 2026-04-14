---
name: build
description: "Multi-session protocol model construction from RFC to formal Ivy model. Use when starting a new protocol spec, scaffolding layers, or continuing a build session."
---

## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
your active workflow overlay and phase modifier. Do not invent your own
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.

# Build Workflow

Read `.panther-ivy/active-workflow` on every turn to determine your current phase. Update the phase field as you transition.

---

## Phase 1 — Scope

### Step 1: Detect methodology context

Look for NCT/NACT/NSCT keywords in the user's request. If none found, ask: "Which testing methodology? NCT (compliance), NACT (security), or NSCT (simulation)."

Load the `methodology-reference` knowledge skill via the Skill tool for methodology details.

### Step 2: Identify target

Determine from the user's request or by asking:

- Protocol name (e.g., QUIC, BGP, CoAP)
- RFC number(s) to model
- Specific aspect or feature to target (e.g., "stream flow control", "connection migration")

### Gate checkpoint

Confirm understanding before proceeding: "I'll build a [methodology] model for [protocol] targeting [RFC]. Correct?"

Wait for explicit confirmation.

### Multi-Perspective Exploration — Architectural Approach

After the user confirms the scope, load the `reflection-patterns` skill. Apply **Pattern B (Multi-Perspective Exploration)**:

- **Exploration question:** "What architectural approach should we use for this [protocol] model?"
- **Agents:**
  - **Conservative Architect** (Explore): Propose a comprehensive model covering all RFC MUST requirements with full invariant coverage. Prioritize correctness over speed.
  - **Pragmatic Engineer** (Explore): Propose a minimal viable model — only the layers needed for the first end-to-end test. Build incrementally.
  - **Adversarial Auditor** (Explore): Propose a security-focused model prioritizing attack surface coverage (NACT-relevant layers, edge cases, error paths).

The user's choice shapes the blueprint in Phase 2.

### Step 3: Update state

Update phase to `"scoped"` via `update_workflow_phase()`.

---

## Phase 2 — Blueprint

### Step 1: Load patterns

Load the `specification-patterns` knowledge skill via the Skill tool.

### Step 2: Scan existing specs

Look in `protocol-testing/{protocol}/` for what already exists:

```
Glob(pattern="*.ivy", path="protocol-testing/{protocol}/")
```

Check for existing `build-state.yaml`:

```python
get_build_state(protocol_dir)
```

### Step 3: Propose layer structure

Using the 14-layer template from the `specification-patterns` skill, propose which layers apply to the target protocol and aspect:

- Which of the 14 layers are needed
- Dependency order for construction
- Minimum viable set (typically 7 layers: Types, Frame, Packet, Connection, Entity Defs, Entity Behavior, Shims)
- Which layers already exist and can be reused

### Situation Briefing — Blueprint Approval

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)** as the gate checkpoint (do not proceed without explicit approval):

- **What happened:** Summarize the blueprint: how many layers proposed, which are new vs. reusable, estimated build order.
- **What it means:** Compare with the MPE recommendations from Phase 1 — which agent's approach was followed and why.
- **Options:** "Approve this blueprint and start writing" / "Adjust layer selection" / "Switch to a different architectural approach"

### Step 4: Write build state

Write `build-state.yaml` to `<protocol_dir>/.panther-ivy/build-state.yaml` via `set_build_state()`:

```yaml
workflow: build
protocol: {protocol}
methodology: {nct|nact|nsct}
started: {ISO datetime}
layers:
  {layer_name}: { status: pending, file: {filename} }
  ...
decisions:
  - "reason for layer choices"
```

### Step 5: Update state

Update phase to `"blueprint-done"` via `update_workflow_phase()`.

---

## Phase 3 — Write

### Step 1: Load writing guidance

Load the `ivy-writing-guide` knowledge skill via the Skill tool.

### Step 2: Generate specs incrementally

Write spec files ONE layer at a time, in dependency order (Types first, then Frame, Packet, etc.).

After writing EACH layer:

1. Run `ivy_compile` for a compile check on the new file.
2. **On compile error:**
   - Dispatch the `spec-analyst` agent with the full error output.
   - If the error involves counterexample interpretation, load the `counterexample-guide` skill.
   - Fix inline (no workflow switch). Loop compile-fix until the layer compiles cleanly.
3. **On compile success:**
   - Update the layer's status in `build-state.yaml` to `"complete"` via `set_build_state()`.

### Inform-and-continue checkpoint between layers

After each layer compiles successfully, give a brief status update: "[N/M] layers complete. Moving to [next layer]." Continue unless the user stops you.

### Reflection Gate — Every 3 Layers

After every 3rd completed layer, load the `reflection-patterns` skill. Apply **Pattern A (Reflection Gate)**:

- **Current state:** "[N/M] layers complete. Layers built so far: [list]. Remaining: [list]."
- **Re-evaluate:** Is the approach working? Did compile errors in the last 3 layers suggest a pattern problem? Has the user's understanding changed?
- **Alternative workflows:**
  - `verify`: "Run verification on what we have so far before continuing"
  - Stay in `build`: "Continue writing the next 3 layers"
  - `review`: "Check coverage of the layers built so far"

### Step 3: Handle type propagation

If the user mentions a type change that affects other layers, load the `propagation-patterns` skill for impact analysis before making changes.

### Step 4: Update state

After all layers are written and compile, update phase to `"written"` via `update_workflow_phase()`.

### Knowledge Gate: Post-Write

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on Ivy patterns discovered while writing layers
- Capture any non-obvious constructs, anti-patterns, or verification feedback
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Phase 4 — Verify

Invoke the `verify` workflow as a sub-workflow.

### Step 1: Set sub-workflow state

Before invoking, update the active-workflow flag:

- `workflow = "verify"`
- `phase = "init"`
- `invocation_depth` = current depth + 1
- `caller = "build"`

### Step 2: Invoke verify

Invoke: `Skill(skill="verify")`

Verify runs its full cycle (test selection, compile, execute, diagnose). On completion, verify returns here because `caller = "build"` and `invocation_depth > 0`.

### Step 3: Restore state

After verify returns, restore the active-workflow flag:

- `workflow = "build"`
- `phase = "verified"`

---

## Phase 5 — Quality Gate

### Step 1: Dispatch review agents in parallel

Dispatch both agents in a single message using two Agent tool calls:

1. **`model-reviewer`** agent: structural correctness, type safety, invariant completeness, action well-formedness, initialization, organization
2. **`traceability-agent`** agent: RFC coverage check against the blueprint's target RFC(s)

### Step 2: Aggregate findings

Collect findings from both agents. Classify by severity: critical, important, suggestion.

### Gate checkpoint on critical issues

If critical issues are found, present them to the user: "These critical issues were found: [list]. Fix them now? Or accept and move on?"

Wait for explicit confirmation.

### Step 3: Handle fixes

If the user wants fixes:

- For structural issues (type safety, invariants, initialization): loop back to Phase 3 to fix the affected layers.
- For verification issues (failed properties, counterexamples): loop back to Phase 4 to re-verify.
- For coverage gaps: add missing monitors inline, then re-run the traceability check.

### Situation Briefing — Quality Gate Results

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)**:

- **What happened:** Summarize the quality gate results: how many findings by severity (critical/important/suggestion), which agents found what, overall model health.
- **What it means:** Are critical issues blocking? Is coverage sufficient for the target methodology?
- **Options:**
  - "Fix critical issues now" (if any exist)
  - "Proceed to wrap-up — accept current quality level"
  - "Run full verification before wrapping up"
  - "Review coverage gaps in detail"

### Step 4: Update state

Update phase to `"quality-passed"` via `update_workflow_phase()`.

### Knowledge Gate: Post-Quality-Gate

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on architecture decisions solidified during quality review
- Capture model-reviewer and traceability-agent findings worth remembering
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Phase 6 — Wrap-up

### Step 1: Summarize

Present a summary of what was built:

- Layers completed (with file paths)
- Verification status (pass/fail per test)
- Coverage statistics (MUST/SHOULD/MAY covered)
- Key design decisions recorded in `build-state.yaml`

### Step 2: Clear state

Clear the active-workflow flag via `clear_active_workflow()`.

### Step 3: Return to navigate

Navigate re-activates on the next user turn and offers context-appropriate next steps based on the completed build.

---

## Multi-Session State

`build-state.yaml` is the persistence mechanism for multi-session builds:

- **Written at:** Phase 2 (blueprint)
- **Updated during:** Phase 3 (layer statuses set to `"complete"` as each layer compiles)
- **Read on resume:** Navigate reads this file in its warm-resume branch (Branch A) and dispatches back to build at the appropriate phase

On session resume, actual progress is inferred from the file system: which `.ivy` files exist, combined with the layer statuses in `build-state.yaml`. The phase field in `active-workflow` indicates which phase to resume from.

---

## Integration

- **Called by:** `navigate` (dispatch), user directly ("build a model", "scaffold a protocol")
- **Calls:** `verify` (post-build verification), `spec-analyst` agent (compile error diagnosis), `model-reviewer` agent (quality gate), `traceability-agent` agent (coverage gate)
- **Knowledge skills loaded:** `reflection-patterns` (MPE Phase 1, SB Phase 2, RG Phase 3, SB Phase 5), `methodology-reference` (Phase 1), `specification-patterns` (Phase 2), `ivy-writing-guide` (Phase 3), `counterexample-guide` (Phase 3 on error), `propagation-patterns` (Phase 3 on type change), `knowledge-capture` (KG Phase 3, KG Phase 5)
- **MCP tools used:** `ivy_compile`, `ivy_workspace`
- **State files:** `.panther-ivy/active-workflow`, `.panther-ivy/build-state.yaml`
