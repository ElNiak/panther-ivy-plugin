---
name: ivy-toolkit
description: "Internal knowledge skill — 22-tool catalog, parameter matrix, selection guide, LSP patterns. Do not invoke directly; loaded by all workflows needing MCP tool calls."
allowed-tools: "Read Grep Glob ToolSearch"
---

# Ivy Toolkit

Single source of truth for Ivy tool operations. All skills and commands reference this
skill instead of maintaining their own tool documentation.

## Iron Law

**NEVER invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` directly via Bash.**
ALWAYS use the ivy-tools MCP equivalents. The PreToolUse hook enforces this, but
you should know it proactively.

## Tool Architecture

Three complementary tool systems:

| System | Purpose | Examples |
|--------|---------|---------|
| **Native Ivy LSP** | Navigation, diagnostics, go-to-definition | documentSymbol, definition, references, hover |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_verify, ivy_compile, ivy_model_info, ivy_diagnostics |
| **Claude native tools** | File I/O, search, editing | Read, Write, Edit, Grep, Glob |

**Workflow:** Navigate (LSP) -> Understand (LSP+MCP) -> Edit (Claude) -> Verify (MCP)

## Quick Tool Reference

| MCP Tool | Purpose | When to Use | Mode |
|----------|---------|-------------|------|
| `ivy_verify` | Formal verification | After writing/modifying specs | FAST + DEEP |
| `ivy_compile` | Compile to test binary | After verification passes | FAST + DEEP |
| `ivy_model_info` | Show model structure | Understanding a spec file | FAST |
| `ivy_diagnostics` | Structural check (mode="structural") or full 5-layer (mode="full") | Before full verification / deep analysis | FAST + DEEP |
| `ivy_include_graph` | Show include dependencies | Phase 1 exploration | DEEP |
| `ivy_capabilities` | Check server capabilities | Diagnostics | FAST |
| `ivy_coverage` | Requirement coverage stats | Phase 1 + Phase 5 | DEEP |
| `ivy_extract_requirements` | Extract RFC requirements | Phase 2 planning | DEEP |
| `ivy_visualize` | Dependency visualization | Understanding architecture | FAST |
| `ivy_model_summary` | Summarize model | Quick overview | FAST |
| `ivy_patterns` | Detect formal patterns | Pattern analysis | FAST |
| `ivy_pattern_scaffold` | Generate from template | Scaffolding new specs | FAST |
| `ivy_quality` | Quality score | Phase 4 verification | DEEP |
| `ivy_health_check` | Server health status | Pre-flight check before tool use | FAST |
| `ivy_scope` | Show workspace scope for a protocol | Workspace management | FAST |
| `ivy_index` | Index protocol files into workspace | Workspace initialization | FAST |
| `ivy_manifest` | Show/generate protocol manifest | Protocol inventory | FAST |
| `ivy_verification_dashboard` | Overview of verification state | Phase 4 reporting | DEEP |
| `ivy_find_variants` | Find all variants of a type | Type analysis | FAST |
| `ivy_serdes_correlation` | Correlate serializer/deserializer for a type | Ser/des analysis | FAST |
| `ivy_change_impact` | Assess impact of changing a type | Change analysis | DEEP |

## Mode Mapping

**FAST mode tools** -- safe for single-operation commands (/nct-check, /nct-model-info):
- ivy_verify, ivy_compile, ivy_model_info, ivy_diagnostics(mode="structural"), ivy_capabilities,
  ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold

**DEEP mode tools** -- used during orchestrated workflows (build, verify, review):
- ivy_diagnostics (full analysis), ivy_include_graph (Phase 1),
  ivy_coverage (Phase 1+5), ivy_extract_requirements (Phase 2),
  ivy_quality (Phase 4)
- All FAST tools are also available in DEEP mode

## LSP Operations

The Ivy LSP provides these operations through the native LSP tool:

| Operation | Purpose |
|-----------|---------|
| `textDocument/documentSymbol` | File outline (types, relations, functions, actions) |
| `textDocument/definition` | Jump to symbol definition |
| `textDocument/references` | Find all references to a symbol |
| `textDocument/hover` | Type signature and documentation |
| `workspace/symbol` | Search symbols across workspace |
| `textDocument/diagnostic` | Real-time syntax/type errors |
| `textDocument/implementation` | Action to before/after monitors |
| `callHierarchy/incomingCalls` | Who calls this action |
| `callHierarchy/outgoingCalls` | What this action calls |

## Coverage Tool Scoping

> **Workspace**: For accurate scoping, first activate the workspace with `/set-workspace <protocol>`. All tool paths are workspace-relative.

The `ivy_coverage` tool accepts different scoping parameters:

| Parameter | Scoping Semantics | Use When |
|---|---|---|
| `relative_path` | Directory-prefix filtering | Browsing a subdirectory |
| `test_file` | Endpoint-mirror scoping (transitive include closure) | NCT-aligned per-endpoint coverage |
| `protocol` | Directory-prefix `protocol-testing/{protocol}/` | Filtering by protocol |

**Recommendation**: Use `test_file` for accurate NCT-aligned results.

## Enforcement

- The **PreToolUse hook** (`block-direct-ivy.sh`) intercepts direct CLI invocations
- If blocked, use the MCP equivalent from the table above
- The hook provides a helpful redirect message with the correct MCP tool name

### Tool Selection Decision Matrix

*(Merged from tooling-reference)*

| Task | Best Tool | Why |
|------|-----------|-----|
| Find where a symbol is defined (across includes) | LSP `goToDefinition` | Resolves includes; Grep only matches text |
| Find all usages of a symbol | LSP `findReferences` | Scope-aware; Grep matches comments too |
| Get action signature / type info | LSP `hover` | Shows params, types, docs |
| List all symbols in a file | LSP `documentSymbol` | Structured outline with hierarchy |
| Search for a symbol by name across workspace | LSP `workspaceSymbol` | Semantic, not text-based |
| Search for a regex pattern across files | Grep | LSP does not support regex |
| Check coverage / traceability | MCP `ivy_coverage` (mode=stats/gaps/matrix) | Structured coverage data |
| Verify formal properties | MCP `ivy_verify` | Structured JSON diagnostics |
| Get diagnostics/errors | MCP `ivy_diagnostics` (mode="structural" for fast check, or full 5-layer) | LSP pushes structural diagnostics on edit; PostToolUse hook provides fallback |

### Coordination Workflows

### Workflow A: Understanding a Symbol Fully
1. `workspaceSymbol` -- find the symbol by name
2. `goToDefinition` -- read its full definition
3. `hover` -- get type signature and docs
4. `findReferences` -- see all usages across workspace
5. LSP `incomingCalls`/`outgoingCalls` -- see incoming/outgoing call edges

### Workflow B: Adding a New Requirement Monitor
1. `documentSymbol` or `workspaceSymbol` -- find the relevant action
2. `findReferences` -- find existing before/after monitors
3. `Read` -- read the existing monitors to understand the pattern
4. MCP `ivy_coverage` (mode="stats") -- check what requirements are missing
5. `Edit` -- write the new monitor with bracket tag
6. MCP `ivy_diagnostics(mode="structural")` -- fast structural check after edit
7. MCP `ivy_verify` -- formal verification
8. MCP `ivy_coverage` (mode="matrix") -- confirm new requirement is covered

### Workflow C: Diagnosing a Verification Failure
1. Read the error message -- note file, line, symbol name
2. `goToDefinition` -- jump to the failing symbol's definition
3. `hover` -- check type signatures for mismatches
4. `findReferences` -- find all monitors that constrain this symbol
5. MCP `ivy_diagnostics` -- get the full 5-layer diagnostic analysis
6. `Edit` -- fix the issue
7. MCP `ivy_verify` -- re-verify

---

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

## Reference Files

- **references/tool-catalog.md** -- Full parameter documentation, outputs, and examples for every MCP tool

## Integration

- **LOADED BY:** All workflow skills and agents
- **SUPERSEDES:** Duplicated tool sections previously in methodology-reference and other deleted skills (merged from tooling-reference)
