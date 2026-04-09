# Build Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Explanatory. Provide reasoning for layer choices and dependency order.
- **Tone**: Methodical. "Layer 4 (frame) depends on types (layer 1). Writing quic_frame.ivy."
- **Structure**: Progress-oriented. Layer tables, dependency chains.

## Mandatory Sections
- **Layer Progress** -- table from build-state.yaml showing status per layer
- **Current Layer** -- what's being worked on, dependencies satisfied
- **Next Steps** -- next layer in dependency order

## Tool Presentation
- `ivy_verify`: per-layer -- "Layer verified: {isolate} PASS" or "Layer verification failed -- switching to verify workflow."
- `ivy_diagnostics`: focus on current layer's structural issues
- `ivy_compile`: compilation of current layer, success/failure

## Phase Modifiers

### scope
- Show protocol overview and methodology selection (NCT/NACT/NSCT).

### blueprint
- Show full 14-layer template, mark which layers are planned vs. skipped.
- Present dependency graph as ordered list.

### write
- Show current layer context: what it does, what it depends on, what depends on it.
- After each file write, show file path and line count.

### quality_gate
- Show quality gate results as pass/fail checklist.

### wrap_up
- Show final layer progress table with all statuses.
