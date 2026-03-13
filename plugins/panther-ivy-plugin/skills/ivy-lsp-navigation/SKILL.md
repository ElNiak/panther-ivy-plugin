---
name: ivy-lsp-navigation
description: Use when navigating Ivy specifications with LSP operations or deciding between LSP, Grep, and MCP for a navigation task
---

# Ivy LSP Navigation

## Quick Reference: When to Use What

| Task | Best Tool | Why |
|------|-----------|-----|
| Find where a symbol is defined (across includes) | LSP `goToDefinition` | Resolves includes; Grep only matches text |
| Find all usages of a symbol | LSP `findReferences` | Scope-aware; Grep matches comments too |
| Get action signature / type info | LSP `hover` | Shows params, types, docs |
| List all symbols in a file | LSP `documentSymbol` | Structured outline with hierarchy |
| Search for a symbol by name across workspace | LSP `workspaceSymbol` | Semantic, not text-based |
| Find what calls a function | LSP `incomingCalls` | Semantic call graph; Grep misses indirect calls |
| Search for a regex pattern across files | Grep | LSP does not support regex |
| Read entire file contents | Read | LSP returns metadata, not content |
| Find comments, strings, non-symbol text | Grep | LSP operates on symbols only |
| Check coverage gaps or traceability | MCP `ivy_coverage_gaps` / `ivy_traceability_matrix` | Analysis tools, not navigation |
| Verify formal properties | MCP `ivy_verify` | Verification, not navigation |
| Get diagnostics/errors | MCP `ivy_lint` or `ivy_diagnostics` | Claude Code does NOT receive automatic LSP diagnostics |

## LSP Tool API

The LSP tool requires all four parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `operation` | string | One of the supported operations (see below) |
| `filePath` | string | Absolute or relative path to the `.ivy` file |
| `line` | integer | 1-based line number |
| `character` | integer | 1-based character offset |

**Operations**: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`

**Position tips**:
- For `documentSymbol`: use `line=1, character=1` — position is ignored, returns all symbols in the file.
- For all other operations: position must point at the symbol of interest.
- Use `documentSymbol` first to discover symbols and their line/character positions.
- Use line numbers from `Read` output (shown as `N>` prefix) to determine positions.
- Results from one LSP call provide positions usable in subsequent calls.

## Invocation Patterns

### Pattern 1: Discover File Structure -- `documentSymbol`

When opening an unfamiliar `.ivy` file, start here to get the full symbol outline:

```
LSP(operation="documentSymbol", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=1, character=1)
```

Returns nested hierarchy: types, objects, actions, modules, relations, functions.

### Pattern 2: Find Symbol by Name -- `workspaceSymbol`

When you know the name but not the file, point at any occurrence of the name:

```
LSP(operation="workspaceSymbol", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=109, character=8)
```

Searches across all indexed `.ivy` files in the workspace.

### Pattern 3: Jump to Definition -- `goToDefinition`

When you see a symbol reference and need its definition:

```
LSP(operation="goToDefinition", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=104, character=10)
```

Key advantage: resolves across `include` boundaries. When `quic_application.ivy` references `cid` defined in `quic_types.ivy`, `goToDefinition` navigates there directly. Grep would match every occurrence of "cid" in every file.

### Pattern 4: Find All References -- `findReferences`

When you need to find all usages of a symbol (all monitors, all callers):

```
LSP(operation="findReferences", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=109, character=8)
```

Returns all before/after/around monitors, call sites, and type references across the workspace.

### Pattern 5: Get Type Info -- `hover`

When you need parameter types, return types, or documentation:

```
LSP(operation="hover", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=109, character=8)
```

Shows: `action map_cids(dcid:cid, scid:cid)` -- reveals parameter names and types without reading the file.

### Pattern 6: Trace Call Hierarchy -- `prepareCallHierarchy` + `incomingCalls`/`outgoingCalls`

For understanding call chains:

```
# Step 1: Get call hierarchy item
LSP(operation="prepareCallHierarchy", filePath="...", line=109, character=8)
# Step 2: Find what calls this
LSP(operation="incomingCalls", filePath="...", line=109, character=8)
# Step 3: Find what this calls
LSP(operation="outgoingCalls", filePath="...", line=109, character=8)
```

## LSP + MCP Coordination Workflows

### Workflow A: Understanding a Symbol Fully

1. `workspaceSymbol` -- find the symbol by name
2. `goToDefinition` -- read its full definition
3. `hover` -- get type signature and docs
4. `findReferences` -- see all usages across workspace
5. MCP `ivy_impact_analysis` -- see incoming/outgoing semantic edges
6. MCP `ivy_cross_references` -- explore graph neighborhood

### Workflow B: Adding a New Requirement Monitor

1. `workspaceSymbol` or `documentSymbol` -- find the relevant action
2. `findReferences` -- find existing before/after monitors for that action
3. `Read` -- read the existing monitors to understand the pattern
4. MCP `ivy_requirement_coverage` -- check what requirements are missing
5. `Edit` -- write the new before/after monitor with bracket tag
6. MCP `ivy_lint` -- runs automatically via post-write hook; also call manually
7. MCP `ivy_verify` -- formal verification
8. MCP `ivy_traceability_matrix` -- confirm the new requirement is now covered

### Workflow C: Diagnosing a Verification Failure

1. Read the error message -- note the file, line, and symbol name
2. `goToDefinition` -- jump to the failing symbol's definition
3. `hover` -- check type signatures for mismatches
4. `findReferences` -- find all monitors that constrain this symbol
5. `incomingCalls` -- trace what actions call into the failing one
6. MCP `ivy_diagnostics` -- get the full 5-layer diagnostic analysis
7. `Edit` -- fix the issue
8. MCP `ivy_verify` -- re-verify

## What LSP Does NOT Provide in Claude Code

- **No automatic diagnostics**: Claude Code does not support `textDocument/publishDiagnostics`. You will NOT see parse errors, missing includes, or structural warnings automatically.
- **Use MCP tools instead**: Run `ivy_lint` (fast, milliseconds) or `ivy_diagnostics` (thorough, 5-layer analysis) after edits.
- **Post-write hook**: The plugin's PostToolUse hook runs `ivy_lint` automatically after any `.ivy` file Write or Edit -- but always check the output for warnings.

## Integration

**Related skills:**
- **panther-ivy:ivy-tooling-guide** — High-level tooling architecture
- **panther-ivy:ivy-lsp-walkthrough** — End-to-end example using these patterns
- **panther-ivy:ivy-tools-reference** — MCP tool alternatives to LSP

**Related agents:**
- **spec-explorer** — Uses LSP for specification navigation
