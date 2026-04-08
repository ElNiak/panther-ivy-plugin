---
name: navigate
description: "Central hub workflow — detects context, presents options, and routes to the appropriate workflow. Activated when the user's intent is unclear, when resuming a session, or when another workflow completes."
---

# Navigate Workflow

Read `.panther-ivy/active-workflow` on every turn to determine your current phase before proceeding. If the file says you are in a phase, resume that phase directly.

Navigate is the central hub. Every other workflow returns here on completion. Navigate dispatches to a workflow which eventually returns to navigate — it never returns to itself.

---

## Phase 1 — Silent Context Scan

Do not produce user-facing output during this phase. Gather context silently.

### Step 1: Locate the protocol directory

Use `find_protocol_dir()` from `hooks/scripts/workflow_state.py` to resolve the protocol directory. If not found, fall through to the cold-start branch in Phase 2.

### Step 2: Check for active build

Read `.panther-ivy/build-state.yaml` via `get_build_state(protocol_dir)`. Record whether a build is in progress, its protocol, methodology, and layer completion status.

### Step 3: Check recent Ivy changes

```bash
git log --oneline -5 -- '*.ivy'
```

Record the results. If there are recent changes, note which files and when.

### Step 4: Run triage preflight

Invoke the `triage` workflow as a sub-workflow to confirm stack health before proceeding:

1. Read the current active-workflow state (if any)
2. Set a new active-workflow flag:
   - `workflow = "triage"`
   - `phase = "preflight"`
   - `invocation_depth = 1`
   - `caller = "navigate"`
3. Invoke: `Skill(skill="triage")`
4. Triage runs Phase 1 only (because `invocation_depth > 0`). If the stack is healthy, it returns silently. If the stack is broken, triage handles diagnosis and repair interactively before returning.
5. After triage returns, restore navigate's active-workflow state:
   - `workflow = "navigate"`
   - `phase = "context-scan"`

---

## Phase 2 — Branch by Context

Based on the context gathered in Phase 1, choose exactly ONE of the three branches below. Evaluate them in order and take the first match.

### Branch A: Warm Resume

**Condition:** `build-state.yaml` exists and contains an in-progress build.

1. Read the build state: workflow, protocol, methodology, layers with their completion status.
2. Infer actual progress from the file system:
   - Which `.ivy` files exist under the protocol directory
   - Run `ivy_diagnostics(mode="structural")` on recently modified files to check compilation status
3. Present a progress summary to the user:
   ```
   You're in the middle of building the [protocol] model using [methodology].
   [N/M] layers complete. Last session ended at [layer/phase context].
   Pick up where you left off? Or do something else?
   ```
4. Wait for user response:
   - **Pick up:** Dispatch to the appropriate workflow (usually `build`), setting the active-workflow flag via `set_active_workflow(protocol_dir, workflow_name, phase="resume")`
   - **Something else:** Proceed to the user interview below, then dispatch based on their answer

### Branch B: Activity Summary

**Condition:** No `build-state.yaml`, but `git log` found recent `.ivy` changes.

1. Summarize what happened since the last session:
   ```
   Last session you [modified/created/verified] [file list].
   [Brief summary of changes from git log.]
   ```
2. Offer context-appropriate next steps:
   - If changes look like spec edits: "Want to verify these changes? Or continue working on the spec?"
   - If changes look like test additions: "Want to run the tests? Or review coverage?"
3. Wait for user response, then dispatch based on their choice.

### Branch C: Cold Start

**Condition:** Neither build state nor recent Ivy changes found.

Interview the user with 1-3 focused questions. Ask one question at a time.

1. **What protocol?** "Which protocol are you working with?" (Skip if the workspace is already set or there's only one protocol directory.)
2. **What's your goal?** "What would you like to do?" Offer concise options:
   - Build a new protocol model
   - Continue or extend an existing model
   - Verify or debug a specification
   - Review coverage or quality
   - Learn about the methodology
3. **Which methodology?** "Which testing approach?" NCT (compliance), NACT (security), or NSCT (simulation). Skip if implied by the goal or if the user seems unfamiliar with the options — default to NCT.

Dispatch based on answers.

---

## Dispatch

When dispatching to a workflow:

1. Call `set_active_workflow(protocol_dir, workflow_name, phase="init")` to write the active-workflow flag.
2. Invoke the workflow: `Skill(skill="{workflow_name}")`

### Routing Table

| Goal | Dispatch Target |
|------|----------------|
| Build or scaffold a protocol model | `build` workflow |
| Verify or debug a specification | `verify` workflow |
| Review quality or coverage | `review` workflow |
| Diagnose broken tools | `triage` workflow |
| Learn methodology | `methodology-reference` skill |
| Extract RFC requirements | `traceability-agent` agent |

If the user's goal doesn't clearly map to a workflow, ask one clarifying question before dispatching.

---

## Sub-Workflow Return Rule

When a workflow is invoked by another workflow (not by navigate directly):

- The calling workflow sets `invocation_depth += 1` and `caller = calling_workflow` on the active-workflow flag before invoking.
- On completion: if `invocation_depth > 0`, the called workflow decrements depth and returns to `caller`, not to navigate.
- If `invocation_depth == 0`, the workflow clears the active-workflow flag and navigate re-activates on the next user turn.

---

## Integration

- **Called by:** Session start (routing hook), other workflows on completion
- **Calls:** `triage` (preflight), then dispatches to `build`, `verify`, `review`, or skills/agents
- **State files:** `.panther-ivy/active-workflow`, `.panther-ivy/build-state.yaml`
- **Infrastructure:** `hooks/scripts/workflow_state.py` provides all state read/write functions
