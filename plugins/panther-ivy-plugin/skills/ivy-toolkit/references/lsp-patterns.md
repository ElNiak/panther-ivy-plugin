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

## LSP Operation Reference

### hover
Get type information and documentation at a cursor position.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based), character (int, 1-based) |
| Returns | Markdown string with type signature and documentation |
| Tier | instant |
| Rendering | raw |

**Errors:**
- Empty result → symbol not indexed yet or cursor not on a symbol; use `documentSymbol` to discover valid positions
- Server not responding → check `ivy_status(mode="health")`

**When to use:** Validating type signatures during spec review. Prefer `ivy_model_info` for general exploration.

---

### goToDefinition
Navigate to the definition of a symbol.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based), character (int, 1-based) |
| Returns | List of `{ uri, range }` location objects |
| Tier | instant |
| Rendering | raw |

**Errors:**
- Empty list → symbol not in workspace index; check indexing is complete via `ivy_status(mode="health")`
- Resolves to include stdlib → expected behavior for builtin Ivy types

**When to use:** Resolving cross-file definitions during verification failure triage. Prefer `Grep` + `Read` for general navigation outside workflow contexts.

---

### findReferences
Find all usage sites of a symbol across the workspace.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based), character (int, 1-based) |
| Returns | List of `{ uri, range }` location objects |
| Tier | fast |
| Rendering | raw |

**Errors:**
- Empty list → symbol not exported or workspace index incomplete
- Partial results → indexing still in progress; wait and retry after `ivy_status(mode="health")` confirms readiness

**When to use:** Tracing all call sites of an action during refactor or coverage analysis. Prefer `Grep` for simple text-pattern searches.

---

### documentSymbol
List all symbols defined in a file (types, relations, functions, actions, isolates).

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based, use 1), character (int, 1-based, use 1) |
| Returns | List of `{ name, kind, range, selectionRange, children }` symbol objects |
| Tier | instant |
| Rendering | raw |

**Errors:**
- Empty list → file not yet indexed; wait for LSP indexing to complete
- File not found → confirm `filePath` is absolute and within the active workspace

**When to use:** Building a file outline before navigating to specific symbols. Use `line=1, character=1` as the position — position is ignored for this operation.

---

### workspaceSymbol
Search for symbols by name across the entire workspace.

| Field | Value |
|-------|-------|
| Parameters | query (str) |
| Returns | List of `{ name, kind, location }` symbol objects |
| Tier | fast |
| Rendering | raw |

**Errors:**
- Empty list → no symbol matches the query or workspace not fully indexed
- Too many results → narrow the query string

**When to use:** Locating a symbol when you know its name but not its file. Prefer `documentSymbol` when exploring a specific file.

---

### prepareCallHierarchy
Prepare a call hierarchy item at a cursor position as the entry point for `incomingCalls` / `outgoingCalls`.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based), character (int, 1-based) |
| Returns | List of call hierarchy items `{ name, kind, uri, range, selectionRange }` |
| Tier | instant |
| Rendering | raw |

**Errors:**
- Empty list → cursor not on a callable symbol; use `documentSymbol` to find valid positions
- NYI in server → `ivy_status(mode="health")` to confirm server version supports call hierarchy

**When to use:** Entry point before calling `incomingCalls` or `outgoingCalls`. Always call this first to obtain the item handle.

---

### incomingCalls / outgoingCalls
Resolve callers (incomingCalls) or callees (outgoingCalls) for a call hierarchy item.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int, 1-based), character (int, 1-based) |
| Returns | List of `{ from, fromRanges }` (incomingCalls) or `{ to, fromRanges }` (outgoingCalls) |
| Tier | fast |
| Rendering | raw |

**Errors:**
- Empty result → action has no callers/callees in the indexed workspace, or `prepareCallHierarchy` step was skipped
- NYI → check server capabilities via `ivy_status(mode="capabilities")`

**When to use:** Tracing action propagation chains during `build` workflow impact analysis. Prefer `findReferences` for simpler single-level call-site lookup.

---

### When to Use LSP vs MCP

| Need | Use |
|------|-----|
| Symbol type/signature | `LSP hover` (in validation context) or `ivy_model_info` (general) |
| Find definition | `LSP goToDefinition` (in validation) or `Grep` + `Read` (general) |
| All references | `LSP findReferences` (in validation) or `Grep` (general) |
| File structure | `LSP documentSymbol` (in validation) or `ivy_model_info` (general) |
| Model analysis | Always `ivy_diagnostics`, `ivy_visualize(view="summary")` (MCP tools) |
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
