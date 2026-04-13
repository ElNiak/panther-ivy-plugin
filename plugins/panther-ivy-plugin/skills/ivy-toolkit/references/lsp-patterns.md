# LSP Invocation Patterns and Coordination Examples

## LSP Invocation Patterns

> **Policy:** Direct LSP calls are permitted when dispatched by workflow skills (e.g., triage for health checks, verify for diagnostics). All other workflows should use MCP tools + Read/Grep/Glob.

### Supported Operations

| Operation | Use Case | Example |
|-----------|----------|---------|
| `hover` | Type info at cursor position | `LSP(operation="hover", filePath="...", line=N, character=N)` |
| `goToDefinition` | Navigate to symbol definition | `LSP(operation="goToDefinition", filePath="...", line=N, character=N)` |
| `findReferences` | Find all usages of a symbol | `LSP(operation="findReferences", filePath="...", line=N, character=N)` |
| `documentSymbol` | List all symbols in a file | `LSP(operation="documentSymbol", filePath="...")` |
| `workspaceSymbol` | Search symbols across workspace | `LSP(operation="workspaceSymbol", query="symbol_name")` |
| `callHierarchy` | Trace incoming/outgoing calls | `LSP(operation="incomingCalls", filePath="...", line=N, character=N)` |

### LSP Tool API

The LSP tool requires: `operation`, `filePath`, `line` (1-based), `character` (1-based).

**Operations**: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy` (NYI), `incomingCalls` (NYI), `outgoingCalls` (NYI)

**Position tips**: For `documentSymbol` use `line=1, character=1`. For all others, point at the symbol of interest. Use `documentSymbol` first to discover positions.

### Invocation Patterns

```
# Pattern 1: File outline
LSP(operation="documentSymbol", filePath="path/to/file.ivy", line=1, character=1)

# Pattern 2: Find symbol by name
LSP(operation="workspaceSymbol", filePath="any_file.ivy", line=<line>, character=<col>)

# Pattern 3: Jump to definition (resolves across includes)
LSP(operation="goToDefinition", filePath="file.ivy", line=<line>, character=<col>)

# Pattern 4: Find all references
LSP(operation="findReferences", filePath="file.ivy", line=<line>, character=<col>)

# Pattern 5: Get type info
LSP(operation="hover", filePath="file.ivy", line=<line>, character=<col>)
```

### When to Use LSP vs MCP

| Need | Use |
|------|-----|
| Symbol type/signature | `LSP hover` (in validation context) or `ivy_model_info` (general) |
| Find definition | `LSP goToDefinition` (in validation) or `Grep` + `Read` (general) |
| All references | `LSP findReferences` (in validation) or `Grep` (general) |
| File structure | `LSP documentSymbol` (in validation) or `ivy_model_info` (general) |
| Model analysis | Always `ivy_diagnostics`, `ivy_model_summary` (MCP tools) |
| Coverage | Always `ivy_coverage` (MCP tool) |

### Diagnostics in Claude Code

- **Automatic structural diagnostics**: The LSP pushes structural diagnostics immediately on `.ivy` file edits (no debounce).
- **Full diagnostics**: The debounced pipeline delivers complete T1+T2 diagnostics ~150ms after the last edit.
- **Fallback**: If `<new-diagnostics>` blocks are not visible, the PostToolUse hook runs `ivy_diagnostics(mode="structural")` automatically after `.ivy` file writes.
- **Manual**: Run `ivy_diagnostics(mode="structural")` (fast, ms) or `ivy_diagnostics` (thorough, 5-layer) for on-demand analysis.

---

## LSP + MCP Coordination Example

End-to-end walkthrough of adding an RFC requirement (`rfc9000:7.3` — Authenticating Connection IDs) to the QUIC specification. Demonstrates the full plugin toolchain.

### Step 1: Find the Relevant Action (LSP)
- `documentSymbol` on `quic_application.ivy` → get file outline (types, relations, actions)
- `workspaceSymbol` pointing at `original_destination_connection_id` → find CID-related symbols across workspace

### Step 2: Explore Definitions (LSP)
- `goToDefinition` on `map_cids` → navigate to the action body: `map_cids(dcid:cid,scid:cid)` that sets `used_cid`, `connected`, `connected_to`
- `hover` on `map_cids` → confirm parameter types without reading the whole file
- `hover` on `app_server_open_event` → get full action signature

### Step 3: Find Existing Monitors (LSP)
- `findReferences` on `map_cids` → all call sites (inside `around app_server_open_event`)
- `findReferences` on `connected_to` → usage sites in behavior files (`ivy_quic_client_server_behavior.ivy`, `ivy_quic_server_behavior.ivy`)
- `findReferences` on `initial_source_connection_id` → config files and test files

### Step 4: Check Coverage Gaps (MCP)
- `ivy_coverage(mode="stats")` → coverage by RFC section and normative level
- `ivy_coverage(mode="gaps")` → unguarded state variables, uncovered RFC requirements

### Step 5: Write the New Monitor (Edit)
Insert an `after` monitor with bracket tag `# [rfc9000:7.3]` in the behavior file.

### Step 6: Lint (MCP)
PostToolUse hook runs `ivy_diagnostics(mode="structural")` automatically. Also run manually for certainty.

### Step 7: Verify (MCP)
`ivy_verify` on the behavior file → confirm the new monitor is consistent with the existing model.

### Step 8: Check Traceability (MCP)
`ivy_coverage(mode="matrix")` → confirm `rfc9000:7.3` now appears as covered.

### Key Takeaways

| Phase | Tools Used | Purpose |
|-------|-----------|---------|
| **Navigation** (Steps 1-3) | LSP (documentSymbol, workspaceSymbol, goToDefinition, findReferences, hover) | Understand code semantically |
| **Analysis** (Step 4) | MCP (ivy_coverage mode="stats", mode="gaps") | Identify what's missing |
| **Editing** (Step 5) | Edit | Write the new monitor |
| **Validation** (Steps 6-8) | MCP (ivy_diagnostics, ivy_verify, ivy_coverage mode="matrix") | Confirm correctness and traceability |
