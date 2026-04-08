---
name: lsp-patterns
description: "DEPRECATED — absorbed into ivy-toolkit. Will be removed in a future version."
---

# LSP Invocation Patterns (Scoped Access)

> **Policy:** Direct LSP calls are permitted only in validation/health-check commands and the `ivy-lsp-walkthrough` skill. All other workflows should use MCP tools + Read/Grep/Glob.

## Supported Operations

| Operation | Use Case | Example |
|-----------|----------|---------|
| `hover` | Type info at cursor position | `LSP(operation="hover", filePath="...", line=N, character=N)` |
| `goToDefinition` | Navigate to symbol definition | `LSP(operation="goToDefinition", filePath="...", line=N, character=N)` |
| `findReferences` | Find all usages of a symbol | `LSP(operation="findReferences", filePath="...", line=N, character=N)` |
| `documentSymbol` | List all symbols in a file | `LSP(operation="documentSymbol", filePath="...")` |
| `workspaceSymbol` | Search symbols across workspace | `LSP(operation="workspaceSymbol", query="symbol_name")` |
| `callHierarchy` | Trace incoming/outgoing calls | `LSP(operation="incomingCalls", filePath="...", line=N, character=N)` |

## LSP Tool API

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

## When to Use LSP vs MCP

| Need | Use |
|------|-----|
| Symbol type/signature | `LSP hover` (in validation context) or `ivy_model_info` (general) |
| Find definition | `LSP goToDefinition` (in validation) or `Grep` + `Read` (general) |
| All references | `LSP findReferences` (in validation) or `Grep` (general) |
| File structure | `LSP documentSymbol` (in validation) or `ivy_model_info` (general) |
| Model analysis | Always `ivy_diagnostics`, `ivy_model_summary` (MCP tools) |
| Coverage | Always `ivy_coverage` (MCP tool) |

## Diagnostics in Claude Code

- **Automatic structural diagnostics**: The LSP pushes structural diagnostics immediately on `.ivy` file edits (no debounce).
- **Full diagnostics**: The debounced pipeline delivers complete T1+T2 diagnostics ~150ms after the last edit.
- **Fallback**: If `<new-diagnostics>` blocks are not visible, the PostToolUse hook runs `ivy_diagnostics(mode="structural")` automatically after `.ivy` file writes.
- **Manual**: Run `ivy_diagnostics(mode="structural")` (fast, ms) or `ivy_diagnostics` (thorough, 5-layer) for on-demand analysis.
