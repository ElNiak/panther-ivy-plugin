# Build Workflow — Layer Scaffolding Reference

Detailed per-layer writing procedure for Phase 3 of the build workflow.

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
