---
name: tooling-reference
description: "Use when choosing between LSP, MCP tools, and Claude native tools for an Ivy task, looking up tool parameters and usage patterns, or navigating Ivy specifications with LSP operations."
---

# Tooling Reference: LSP, MCP Tools, and Claude Native Tools

This skill combines the tooling architecture guide, the MCP tool parameter reference, and LSP navigation patterns into a single reference.

---

## Architecture

The panther-ivy-plugin provides Ivy code intelligence through two complementary layers:

| Layer | Role | How it works |
|-------|------|-------------|
| **Native Ivy LSP** | Code intelligence via LSP tool | Claude Code runs ivy_lsp as a language server -- go-to-definition, find-references, hover, and document symbols via the `LSP` tool for `.ivy` files |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_lsp runs in MCP mode (`--mcp`) providing structured tool access to ivy_verify, ivy_compile, ivy_model_info, ivy_lint, and more |

For code navigation and editing, use Claude's built-in tools (`Read`, `Edit`, `Write`, `Grep`, `Glob`). The native LSP enriches these with Ivy-specific intelligence.

## Quick Reference: When to Use What

| Task | Best Tool | Why |
|------|-----------|-----|
| Find where a symbol is defined (across includes) | LSP `goToDefinition` | Resolves includes; Grep only matches text |
| Find all usages of a symbol | LSP `findReferences` | Scope-aware; Grep matches comments too |
| Get action signature / type info | LSP `hover` | Shows params, types, docs |
| List all symbols in a file | LSP `documentSymbol` | Structured outline with hierarchy |
| Search for a symbol by name across workspace | LSP `workspaceSymbol` | Semantic, not text-based |
| Find what calls a function | LSP `incomingCalls` | Semantic call graph |
| Search for a regex pattern across files | Grep | LSP does not support regex |
| Read entire file contents | Read | LSP returns metadata, not content |
| Find comments, strings, non-symbol text | Grep | LSP operates on symbols only |
| Check coverage gaps or traceability | MCP `ivy_coverage` (mode="gaps"/"matrix"/"stats") | Analysis tools |
| Verify formal properties | MCP `ivy_verify` | Verification tool |
| Get diagnostics/errors | MCP `ivy_lint` or `ivy_diagnostics` | Claude Code does NOT receive automatic LSP diagnostics |

---

## LSP Tool API

The LSP tool requires all four parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `operation` | string | One of the supported operations |
| `filePath` | string | Absolute or relative path to the `.ivy` file |
| `line` | integer | 1-based line number |
| `character` | integer | 1-based character offset |

**Operations**: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`

**Position tips**:
- For `documentSymbol`: use `line=1, character=1` -- position is ignored, returns all symbols.
- For all other operations: position must point at the symbol of interest.
- Use `documentSymbol` first to discover symbols and their positions.
- Use line numbers from `Read` output to determine positions.

### LSP Invocation Patterns

#### Pattern 1: Discover File Structure -- `documentSymbol`
```
LSP(operation="documentSymbol", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=1, character=1)
```

#### Pattern 2: Find Symbol by Name -- `workspaceSymbol`
```
LSP(operation="workspaceSymbol", filePath="some_file.ivy", line=109, character=8)
```

#### Pattern 3: Jump to Definition -- `goToDefinition`
```
LSP(operation="goToDefinition", filePath="some_file.ivy", line=104, character=10)
```
Key advantage: resolves across `include` boundaries.

#### Pattern 4: Find All References -- `findReferences`
```
LSP(operation="findReferences", filePath="some_file.ivy", line=109, character=8)
```

#### Pattern 5: Get Type Info -- `hover`
```
LSP(operation="hover", filePath="some_file.ivy", line=109, character=8)
```

#### Pattern 6: Trace Call Hierarchy
```
LSP(operation="prepareCallHierarchy", filePath="...", line=109, character=8)
LSP(operation="incomingCalls", filePath="...", line=109, character=8)
LSP(operation="outgoingCalls", filePath="...", line=109, character=8)
```

---

## MCP Tool Catalog

All ivy-tools MCP tools follow this prefix: `mcp__plugin_panther-ivy-plugin_ivy-tools__<tool_name>`

### Verification and Linting

#### ivy_verify
Run `ivy_check` on an Ivy file. Returns structured diagnostics.
```
Parameters:
  relative_path: str           # Path to .ivy file (relative to project root)
  isolate: str | None = None   # Optional isolate name

Returns: { success, diagnostics, diagnostic_count, raw_output, duration_seconds }
```
Timeout: 120 seconds.

#### ivy_compile
Compile an Ivy file to a test executable using `ivyc`.
```
Parameters:
  relative_path: str           # Path to .ivy file
  target: str = "test"         # Compilation target
  isolate: str | None = None   # Optional isolate name

Returns: { success, output, duration_seconds }
```
Timeout: 300 seconds.

#### ivy_model_info
Display model structure using `ivy_show`.
```
Parameters:
  relative_path: str           # Path to .ivy file
  isolate: str | None = None   # Optional isolate name

Returns: { success, output, duration_seconds }
```
Timeout: 30 seconds.

#### ivy_lint
Fast structural lint (no subprocess, milliseconds).
```
Parameters:
  relative_path: str           # Path to .ivy file

Returns: { file, diagnostics, diagnostic_count, error_count, warning_count }
```

#### ivy_diagnostics
Full 5-layer diagnostic analysis (structural, lexer, semantic, coverage, pattern).
```
Parameters:
  relative_path: str
  layers: list[str] | None = None       # Optional: structural, lexer, semantic, coverage, pattern
  min_severity: str | None = None       # Optional: error, warning, info, hint

Returns: { diagnostics, diagnostic_count, by_layer }
```

### Dependency Analysis

#### ivy_include_graph
Return include dependency graph for Ivy files.
```
Parameters:
  relative_path: str | None = None      # Optional file to focus on

Returns (focused): { file, includes, included_by, transitive_includes }
Returns (full): { files, total_files }
```

#### ivy_capabilities
Check which Ivy CLI tools are available on PATH.
```
Parameters: none
Returns: { ivy_check, ivyc, ivy_show }
```

### Traceability and Semantic Analysis (Consolidated)

#### ivy_coverage
Unified coverage and traceability tool with mode dispatch.
```
Parameters:
  mode: str              # "matrix" | "stats" | "gaps" | "diff"
  relative_path: str | None = None
  protocol: str | None = None

Mode "matrix": RFC requirement-to-annotation mapping
Returns: { total_requirements, covered, uncovered, matrix }

Mode "stats": Coverage statistics by MUST/SHOULD/MAY level and layer
Returns: { total, covered, uncovered, coverage_percent, by_level, by_layer }

Mode "gaps": Identify unguarded state vars, uncovered requirements, orphaned monitors
Returns: { unguarded_state_vars, uncovered_requirements, orphaned_monitors, gap_count }

Mode "diff": Compare coverage between baseline and current
Returns: { baseline, current, newly_covered, newly_uncovered }
```

#### ivy_query
Unified semantic query tool with mode dispatch.
```
Parameters:
  mode: str              # "impact" | "xrefs" | "info"
  symbol_name: str | None = None
  node_id: str | None = None

Mode "impact": Incoming and outgoing edges for a symbol (requires symbol_name)
Returns: { symbol, found, qualified_name, kind, file, line, incoming_edges, outgoing_edges, total_references }

Mode "xrefs": Cross-reference graph neighborhood of a node (requires node_id)
Returns: { node_id, found, node_type, incoming, outgoing }

Mode "info": Rich semantic info about a symbol (requires symbol_name)
Returns: { symbol, found, symbol_info, type_info, references }
```

#### ivy_extract_requirements
Parse RFC text for normative statements (MUST/SHOULD/MAY).
```
Parameters:
  relative_path: str | None = None
  output: str = "structured"    # "structured" | "manifest"

Output "structured": Parse RFC text for normative statements
Returns: { requirements, total, by_level }

Output "manifest": Generate YAML requirements manifest
Returns: { yaml, total_requirements, suggested_path, by_level }
```

### Model Visualization (Consolidated)

#### ivy_visualize
Unified model visualization tool with view dispatch.
```
Parameters:
  view: str              # "dependencies" | "state_machine" | "layers"
  relative_path: str | None = None
  protocol: str | None = None

View "dependencies": Action dependency graph via shared state
Returns: { nodes, edges, total_actions }

View "state_machine": State-machine perspective of the model
Returns: { states, transitions, total_states }

View "layers": Layered overview organized by file or module
Returns: { layers, total_files }
```

#### ivy_model_summary
Per-action summary with mode dispatch.
```
Parameters:
  detail: str = "summary"   # "summary" | "requirements"
  relative_path: str | None = None
  protocol: str | None = None

Detail "summary": Per-action requirement counts, state variable usage, RFC coverage
Returns: { rows, total_actions }

Detail "requirements": Requirements organized by action boundaries (before/after monitors)
Returns: { actions, total_actions }
```

### Quality and Patterns (Consolidated)

#### ivy_quality
Unified quality tool with mode dispatch.
```
Parameters:
  mode: str              # "suggestions" | "gate"
  relative_path: str | None = None
  protocol: str | None = None
  level: str = "minimal"    # For gate mode: "minimal" | "standard" | "comprehensive"

Mode "suggestions": Context-aware suggestions for improving an Ivy specification
Returns: { suggestions, total }

Mode "gate": Validate a protocol model against quality gates
Returns: { checks, all_passed, gate_level }
```

#### ivy_patterns
Unified pattern analysis tool with mode dispatch.
```
Parameters:
  mode: str = "analyze"    # "analyze" | "validate" | "compare" | "check"
  protocol: str | None = None
  pattern: str | None = None
  reference_protocol: str | None = None  # Required for "compare" mode

Mode "analyze"/"detect": Analyze formal model patterns in a specification
Returns: { patterns, total_patterns, mode }

Mode "validate": Cross-reference validation of detected patterns
Returns: { patterns, issues, validation_summary }

Mode "compare": Compare patterns between two protocols (requires reference_protocol)
Returns: { protocol_a, protocol_b, comparison }

Mode "check": Check which layers/patterns are present or missing (scaffold check)
Returns: { layers_present, layers_missing, suggestions, completeness_score }
```

#### ivy_pattern_scaffold
Generate Ivy source code from a pattern template.
```
Parameters:
  pattern_type: str, protocol: str | None = None, name: str | None = None

Returns: { source, pattern, file_suggestion }
```

---

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
5. `incomingCalls` -- trace what actions call into the failing one
6. MCP `ivy_diagnostics` -- get the full 5-layer diagnostic analysis
7. `Edit` -- fix the issue
8. MCP `ivy_verify` -- re-verify

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
