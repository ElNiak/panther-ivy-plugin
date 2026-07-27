# LSP operations and coordination workflows

The Ivy LSP exposes navigational and diagnostic operations through Claude Code's native LSP tool. This file documents the operations and the canonical multi-tool coordination workflows. The host skill (`ivy-toolkit`) points here when LSP work is in scope.

## LSP Operations

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

## Coordination Workflows

### Workflow A: Understanding a Symbol Fully
1. `workspaceSymbol` — find the symbol by name
2. `goToDefinition` — read its full definition
3. `hover` — get type signature and docs
4. `findReferences` — see all usages across workspace
5. LSP `incomingCalls` / `outgoingCalls` — see incoming/outgoing call edges

### Workflow B: Adding a New Requirement Monitor
1. `documentSymbol` or `workspaceSymbol` — find the relevant action
2. `findReferences` — find existing before/after monitors
3. `Read` — read the existing monitors to understand the pattern
4. MCP `ivy_coverage(mode="stats")` — check what requirements are missing
5. `Edit` — write the new monitor with bracket tag
6. MCP `ivy_diagnostics(mode="structural")` — fast structural check after edit
7. MCP `ivy_verify` — formal verification
8. MCP `ivy_coverage(mode="matrix")` — confirm new requirement is covered

### Workflow C: Diagnosing a Verification Failure
1. Read the error message — note file, line, symbol name
2. `goToDefinition` — jump to the failing symbol's definition
3. `hover` — check type signatures for mismatches
4. `findReferences` — find all monitors that constrain this symbol
5. MCP `ivy_diagnostics` — get the full 5-layer diagnostic analysis
6. `Edit` — fix the issue
7. MCP `ivy_verify` — re-verify

## Tool Selection Decision Matrix

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
