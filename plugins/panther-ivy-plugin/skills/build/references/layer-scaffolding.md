# Build Workflow — Layer Scaffolding Reference

Detailed per-layer writing procedure for Phase 3 of the build workflow.

---

## Phase 3 — Write

### Step 1: Load writing guidance

Load the `ivy-writing-guide` knowledge skill via the Skill tool.

### Step 2: Generate specs incrementally

Write spec files ONE layer at a time, in dependency order (Types first, then Frame, Packet, etc.).

After writing EACH layer:

1. **Attempt-counter gate** (before each compile attempt):
   - Compute the attempt key as the layer's canonical name from `build-state.yaml.layers` (e.g., `bgp_open`, not the file path).
   - Read the journal: `ivy_workflow_state(action="get_journal", protocol="<protocol>", last_n=200)`.
   - Walk backward to the most recent `decision{kind: "override_attempt_cap", key: <same layer>}` (index `override_idx`, or `-1` if absent).
   - Count `progress{kind: "compile_attempt", key: <same layer>}` entries after `override_idx`.
   - If `count >= 5`, ESCALATE via `AskUserQuestion`:
     - **Continue anyway** — append `decision{kind: "override_attempt_cap", key: "<layer>"}`; the cap re-engages after 5 more attempts.
     - **Abandon this layer** — mark the layer's `build-state.yaml` status as `abandoned`, record `decision{summary: "Abandon <layer> after N attempts"}`, move to the next layer in dependency order.
     - **Switch workflow** — emit `append_pending_dispatch(target_workflow="verify", reason="Compile loop capped on <layer>")` (or `build` if structural rethink is needed), clear the active-workflow flag.
   - Otherwise, append `progress{kind: "compile_attempt", key: "<layer>", protocol: "<protocol>"}` and proceed to step 2.
2. Run `ivy_compile` for a compile check on the new file.
3. **On compile error:**
   - Dispatch the `spec-analyst` agent with the full error output.
   - If the error involves counterexample interpretation, load the `counterexample-guide` skill.
   - Fix inline. Loop back to step 1 (re-evaluate the attempt cap, then recompile).
4. **On compile success:**
   - Update the layer's status in `build-state.yaml` to `"complete"` via `ivy_workflow_state(action="set_build", protocol="<protocol>", state="<JSON>")`.

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

After all layers are written and compile, update phase to `"written"` via `ivy_workflow_state(action="set", workflow="build", phase="written", protocol="<protocol>")`.

### Knowledge Gate: Post-Write

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on Ivy patterns discovered while writing layers
- Capture any non-obvious constructs, anti-patterns, or verification feedback
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Post-Edit Workspace-Block Recovery

After every `Write` / `Edit` on a `.ivy` file during Phase 3 (layer writes), inspect the tool-result for a workspace-scope violation from the `check-workspace-scope.py` PreToolUse hook. If the hook emits a "workspace scope violation" error (or an `additionalContext` marker naming the blocked file), the layer was not written to disk:

1. Append `progress{kind: "workspace_edit_blocked", file: "<path>", workspace_active: "<current>"}` to the journal.
2. Present `AskUserQuestion` with three options (per `.claude/rules/mcp-tool-reliability.md`):
   - **Switch workspace to the file's protocol** — run `/set-workspace <inferred-protocol>`, then retry the Edit. Also update `build-state.yaml`'s `decisions` block if the workspace shift reflects a scope change.
   - **Clear workspace restrictions** — run `/clear-workspace`, then retry the Edit. Appropriate for multi-protocol builds where the layer spans protocols.
   - **Abandon this layer** — skip the Edit, mark the layer's `build-state.yaml` status as `abandoned`, record a `decision` entry, and move to the next layer in dependency order.

Platform note: if the harness does not propagate PreToolUse-hook block signals into the tool-result, this path does not fire. File a platform-level issue if observed; the recovery pattern still applies whenever the signal reaches user-space.
