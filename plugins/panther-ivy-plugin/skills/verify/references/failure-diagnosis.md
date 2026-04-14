# Verify Workflow — Failure Diagnosis Reference

Detailed failure diagnosis and fix procedures for the verify workflow (Phases 6 and 7).

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

Update phase to `"diagnosed"` via `ivy_workflow_state(action="set", workflow="verify", phase="diagnosed", protocol="<protocol>")`.

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

Apply the fix suggested by the spec-analyst. If editing `.ivy` files, invoke the `ivy-writing-guide` skill to load language reference guidance before making changes.

### Step 2: Re-verify

Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) → Phase 4 (execute) → Phase 6 (diagnose) → Phase 7 (fix) → Phase 3 again.

This loop continues until verification passes or the user decides to stop.

### On user stopping

Update phase to `"stopped"` and proceed to completion.

### Knowledge Gate: Post-Fix

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on the bug that was diagnosed and fixed — what was non-obvious?
- Capture the error-to-fix pattern for future sessions
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes
