---
name: tooling-reference
description: "Use when choosing between LSP, MCP tools, and Claude native tools for an Ivy task, looking up tool parameters and usage patterns, or navigating Ivy specifications with LSP operations."
---

# Tooling Reference: LSP, MCP Tools, and Claude Native Tools

## Architecture

| Layer | Role | How it works |
|-------|------|-------------|
| **Native Ivy LSP** | Code intelligence via LSP tool | go-to-definition, find-references, hover, document symbols via the `LSP` tool for `.ivy` files |
| **ivy-tools MCP** | Verification, compilation, analysis | 15 consolidated tools: `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_lint`, `ivy_coverage`, `ivy_query`, `ivy_visualize`, `ivy_quality`, `ivy_patterns`, etc. |
| **Claude native** | Navigation and editing | `Read`, `Edit`, `Write`, `Grep`, `Glob` |

## When to Use What

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
| Get diagnostics/errors | MCP `ivy_lint` or `ivy_diagnostics` | Claude Code does NOT receive automatic LSP diagnostics |

## LSP Tool API

The LSP tool requires: `operation`, `filePath`, `line` (1-based), `character` (1-based).

**Operations**: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy` (NYI), `incomingCalls` (NYI), `outgoingCalls` (NYI)

**Position tips**: For `documentSymbol` use `line=1, character=1`. For all others, point at the symbol of interest. Use `documentSymbol` first to discover positions.

### LSP Invocation Patterns

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

## MCP Tool Catalog (Compact)

All tools use prefix `mcp__plugin_panther-ivy-plugin_ivy-tools__<tool_name>`. See the [README.md](README.md) for full parameter documentation.

| Tool | Modes / Views | Key Parameters |
|------|---------------|----------------|
| `ivy_lint` | -- | relative_path |
| `ivy_verify` | -- | relative_path, isolate |
| `ivy_compile` | -- | relative_path, target, isolate |
| `ivy_model_info` | -- | relative_path, isolate |
| `ivy_diagnostics` | -- | relative_path, layers, min_severity |
| `ivy_include_graph` | -- | relative_path |
| `ivy_capabilities` | -- | (none) |
| `ivy_coverage` | stats, gaps, matrix | relative_path, test_file, protocol |
| `ivy_query` | info, impact, xrefs | symbol_name, node_id |
| `ivy_extract_requirements` | structured, manifest | rfc_text, rfc_name |
| `ivy_visualize` | dependencies, state_machine, layers | test_file |
| `ivy_model_summary` | summary, requirements | test_file, action_name |
| `ivy_quality` | suggestions, gate | file_path, protocol, gate_level |
| `ivy_patterns` | analyze, validate, compare, check | protocol, pattern |
| `ivy_pattern_scaffold` | -- | protocol, pattern |

## LSP + MCP Coordination Workflows

### Workflow A: Understanding a Symbol Fully
1. `workspaceSymbol` -- find the symbol by name
2. `goToDefinition` -- read its full definition
3. `hover` -- get type signature and docs
4. `findReferences` -- see all usages across workspace
5. MCP `ivy_query` (mode="impact") -- see incoming/outgoing semantic edges

### Workflow B: Adding a New Requirement Monitor
1. `documentSymbol` or `workspaceSymbol` -- find the relevant action
2. `findReferences` -- find existing before/after monitors
3. `Read` -- read the existing monitors to understand the pattern
4. MCP `ivy_coverage` (mode="stats") -- check what requirements are missing
5. `Edit` -- write the new monitor with bracket tag
6. MCP `ivy_lint` -- runs automatically via post-write hook
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

### Recommended Workflow: Navigate -> Understand -> Edit -> Verify
1. **Navigate** -- Use LSP to find and follow symbols. Fall back to `Grep` for regex.
2. **Understand** -- Use LSP `hover` for types. Use `Read` for full implementations.
3. **Edit** -- Use `Edit`/`Write`. Run MCP `ivy_lint` after edits.
4. **Verify** -- Use MCP `ivy_verify`, `ivy_compile` to confirm properties hold.

## What LSP Does NOT Provide in Claude Code

- **No automatic diagnostics**: Claude Code does not support `textDocument/publishDiagnostics`.
- **Use MCP tools instead**: Run `ivy_lint` (fast, ms) or `ivy_diagnostics` (thorough, 5-layer) after edits.
- **Post-write hook**: The plugin's PostToolUse hook runs `ivy_lint` automatically after `.ivy` file writes.

## Enforcement

The PreToolUse hook warns about direct Ivy CLI calls in Bash. If a Bash command containing `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` is attempted, the hook prints a suggestion to use MCP equivalents.

Use `/nct-check`, `/nct-compile`, and `/nct-model-info` commands as convenient shortcuts.

## Integration

**Related skills:**
- **ivy-lsp-walkthrough** -- End-to-end example using these patterns
- **ivy-writing-guide** -- Ivy syntax for editing
- **workflow-reference** -- Verification and quality gate workflows
