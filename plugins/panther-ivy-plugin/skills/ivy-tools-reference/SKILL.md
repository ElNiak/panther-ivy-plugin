---
name: ivy-tools-reference
description: Use when looking up parameters, return types, or usage patterns for any of the ivy-tools MCP diagnostic and analysis tools
---

# Ivy Tools Reference -- Diagnostics MCP Server

## Role Division

The panther-ivy-plugin exposes the **ivy-tools** MCP server alongside native tooling:

| Tool Layer | Role | Analogy |
|--------|------|---------|
| **ivy-tools** | Read-only diagnostics and analysis | Like pyright/eslint for Python/JS |
| **Native LSP + Claude tools** | Code navigation, editing, and file operations | Built-in IDE capabilities |

**Use ivy-tools** for: verification, linting, coverage, traceability, dependency graphs.
**Use Claude's built-in tools** (`Read`, `Grep`, `Glob`, `Edit`, `Write`) for: navigate code, edit files, create files. Native Ivy LSP provides go-to-definition, find-references, and hover.

See the `ivy-tooling-guide` skill for detailed tooling guidance.

## Tool Name Pattern

All ivy-tools MCP tools follow this prefix:

```
mcp__plugin_panther-ivy-plugin_ivy-tools__<tool_name>
```

## Tool Catalog

### Verification and Linting

#### ivy_verify

Run `ivy_check` on an Ivy file. Returns structured diagnostics.

```
Parameters:
  relative_path: str           # Path to .ivy file (relative to project root)
  isolate: str | None = None   # Optional isolate name

Returns: JSON {
  success: bool,
  diagnostics: [{file, line, severity, message}, ...],
  diagnostic_count: int,
  raw_output: str,
  duration_seconds: float
}
```

Timeout: 120 seconds. Checks isolate assumptions, invariants, and safety properties.

#### ivy_compile

Compile an Ivy file to a test executable using `ivyc`.

```
Parameters:
  relative_path: str           # Path to .ivy file
  target: str = "test"         # Compilation target
  isolate: str | None = None   # Optional isolate name

Returns: JSON {
  success: bool,
  output: str,
  duration_seconds: float
}
```

Timeout: 300 seconds. Produces a C++ test binary using Z3/SMT.

#### ivy_model_info

Display model structure using `ivy_show`.

```
Parameters:
  relative_path: str           # Path to .ivy file
  isolate: str | None = None   # Optional isolate name

Returns: JSON {
  success: bool,
  output: str,
  duration_seconds: float
}
```

Timeout: 30 seconds. Shows types, relations, actions, invariants, isolates.

#### ivy_lint

Fast structural lint (no subprocess, milliseconds).

```
Parameters:
  relative_path: str           # Path to .ivy file

Returns: JSON {
  file: str,
  diagnostics: [{line, severity, message, source}, ...],
  diagnostic_count: int,
  error_count: int,
  warning_count: int
}
```

Checks: missing `#lang` header, unmatched braces, unresolved includes. No external tools required.

#### ivy_diagnostics

Full diagnostic analysis of an Ivy file (5 layers: structural, lexer, semantic, coverage, pattern). More thorough than `ivy_lint` but may take longer on first call (lazy model/graph building).

```
Parameters:
  relative_path: str                       # Path to .ivy file
  layers: list[str] | None = None          # Optional: structural, lexer, semantic, coverage, pattern
  min_severity: str | None = None          # Optional: error, warning, info, hint

Returns: JSON {
  diagnostics: [{file, line, severity, message, layer}, ...],
  diagnostic_count: int,
  by_layer: {layer: count, ...}
}
```

Use `ivy_lint` for quick structural checks (milliseconds). Use `ivy_diagnostics` for thorough analysis after editing.

### Dependency Analysis

#### ivy_include_graph

Return include dependency graph for Ivy files.

```
Parameters:
  relative_path: str | None = None  # Optional file to focus on

Returns (focused): JSON {
  file: str,
  includes: [{module, resolved_path}, ...],
  included_by: [str, ...],
  transitive_includes: [str, ...]
}

Returns (full project): JSON {
  files: {path: {includes: [str, ...]}},
  total_files: int
}
```

If a file is given, returns its direct includes, files that include it, and transitive closure. If omitted, returns the full project graph.

#### ivy_capabilities

Check which Ivy CLI tools are available on PATH.

```
Parameters: none

Returns: JSON {
  ivy_check: bool,
  ivyc: bool,
  ivy_show: bool
}
```

Use this first to determine which verification tools are available before calling `ivy_verify`, `ivy_compile`, or `ivy_model_info`.

### Traceability and Semantic Analysis

These tools build a semantic model from RFC requirement manifests and bracket-tag annotations in `.ivy` files. The model is built lazily on first use and cached.

#### ivy_traceability_matrix

RFC requirement-to-annotation mapping.

```
Parameters:
  relative_path: str | None = None  # Optional file to scope to

Returns: JSON {
  total_requirements: int,
  covered: int,
  uncovered: int,
  matrix: [{id, rfc, section, level, text, covered, assertions}, ...]
}
```

Shows which RFC requirements have corresponding bracket-tag annotations in the codebase.

#### ivy_requirement_coverage

Coverage statistics by MUST/SHOULD/MAY level and layer.

```
Parameters:
  relative_path: str | None = None  # Optional file to scope to

Returns: JSON {
  total: int,
  covered: int,
  uncovered: int,
  coverage_percent: float,
  by_level: {MUST: {total, covered}, SHOULD: {...}, MAY: {...}},
  by_layer: {layer_name: {total, covered}, ...}
}
```

#### ivy_impact_analysis

Incoming and outgoing edges for a symbol in the semantic model.

```
Parameters:
  symbol_name: str             # Symbol name or qualified name

Returns: JSON {
  symbol: str,
  found: bool,
  qualified_name: str,
  kind: str,
  file: str,
  line: int,
  incoming_edges: [{type, source}, ...],
  outgoing_edges: [{type, target}, ...],
  total_references: int
}
```

#### ivy_extract_requirements

Parse RFC text for normative statements (MUST/SHOULD/MAY).

```
Parameters:
  rfc_text: str                # Raw RFC text to parse

Returns: JSON {
  requirements: [{text, level, offset}, ...],
  total: int,
  by_level: {MUST: int, SHOULD: int, MAY: int, ...}
}
```

Normalizes RFC 2119 keywords: SHALL -> MUST, REQUIRED -> MUST, RECOMMENDED -> SHOULD, OPTIONAL -> MAY.

#### ivy_cross_references

Query cross-reference graph neighborhood of a node.

```
Parameters:
  node_id: str                 # Node ID (e.g., "test.ivy:5:send")

Returns: JSON {
  node_id: str,
  found: bool,
  node_type: str,
  incoming: [{type, source}, ...],
  outgoing: [{type, target}, ...]
}
```

#### ivy_query_symbol

Rich semantic info about a symbol: type, references, requirements.

```
Parameters:
  symbol_name: str             # Symbol name or qualified name

Returns: JSON {
  symbol: str,
  found: bool,
  symbol_info: {qualified_name, kind, file, line, params, return_sort, sort_name},
  type_info: {qualified_name, file, line, sort_name, is_enum, variants},
  references: {incoming: int, outgoing: int}
}
```

Returns symbol details if it exists as a SymbolNode, type details if it exists as a TypeNode, or both.

#### ivy_generate_manifest

Generate a YAML requirements manifest from RFC text. Extracts MUST/SHOULD/MAY requirements and formats them as structured YAML for traceability tools.

```
Parameters:
  rfc_name: str                            # RFC identifier (e.g., "RFC9000")
  rfc_text: str                            # Raw RFC text to parse
  protocol: str = ""                       # Protocol name for layer inference
  base_section: str = ""                   # Default section prefix

Returns: JSON {
  yaml: str,
  total_requirements: int,
  suggested_path: str,
  by_level: {MUST: int, SHOULD: int, MAY: int}
}
```

Output can be saved as `protocol-testing/<protocol>/<rfc>_requirements.yaml`.

### Model Visualization

#### ivy_action_requirements

Get requirements organized by action boundaries (before/after monitors). Returns requirements grouped by the action they monitor, their temporal position, kind, and state variables.

```
Parameters:
  action_name: str | None = None           # Specific action (omit for all)
  file_path: str | None = None             # Scope to actions in this file
  test_file: str | None = None             # Scope to test file includes
  protocol: str | None = None              # Protocol name filter
  offset: int = 0                          # Pagination offset
  limit: int | None = None                 # Max actions to return

Returns: JSON {
  actions: [{name, file, before: [{kind, text, state_vars}], after: [...]}, ...],
  total_actions: int
}
```

#### ivy_model_summary

Per-action requirement counts, state variable usage, and RFC coverage summary table.

```
Parameters:
  test_file: str | None = None             # Scope to test file includes
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  rows: [{action, before_count, after_count, state_vars_read, state_vars_written, rfc_tags}, ...],
  total_actions: int
}
```

#### ivy_coverage_gaps

Identify coverage gaps: unguarded state variables, uncovered RFC requirements, orphaned monitors.

```
Parameters:
  test_file: str | None = None             # Scope to test file includes
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  unguarded_state_vars: [str, ...],
  uncovered_requirements: [{id, level, text}, ...],
  orphaned_monitors: [{action, file}, ...],
  gap_count: int
}
```

#### ivy_action_dependency_graph

Action dependency graph showing shared-state relationships. Actions are nodes; edges represent shared state variables (action A writes a variable that action B reads).

```
Parameters:
  test_file: str | None = None             # Scope to test file includes
  include_state_vars: bool = False         # Include state variable nodes
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  nodes: [{id, type, file}, ...],
  edges: [{source, target, label}, ...],
  total_actions: int
}
```

#### ivy_state_machine_view

State-machine view of the Ivy specification. State variables are state nodes, actions are transitions (via READS/WRITES), guards are require/assume clauses.

```
Parameters:
  test_file: str | None = None             # Scope to test file includes
  state_var_filter: str | None = None      # Filter to specific state variable
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  states: [{name, type, file}, ...],
  transitions: [{action, reads, writes, guards}, ...],
  total_states: int
}
```

#### ivy_layered_overview

Layered overview of the Ivy model organized by file or module.

```
Parameters:
  test_file: str | None = None             # Scope to test file includes
  group_by: str = "file"                   # Grouping: "file" or "module"
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  layers: [{name, files, types, actions, relations}, ...],
  total_files: int
}
```

### Quality and Suggestions

#### ivy_smart_suggestions

Context-aware suggestions for improving an Ivy specification.

```
Parameters:
  file_path: str | None = None             # File to analyze
  line: int | None = None                  # Cursor line for local suggestions
  context: str | None = None               # Hint: "monitor", "property", etc.
  protocol: str | None = None              # Protocol name filter

Returns: JSON {
  suggestions: [{category, message, file, line, severity}, ...],
  total: int
}
```

#### ivy_quality_gate

Validate a protocol model against quality gates (minimal, standard, or comprehensive).

```
Parameters:
  protocol: str                            # Protocol name (e.g., "quic")
  gate_level: str = "minimal"              # Gate: "minimal", "standard", "comprehensive"

Returns: JSON {
  checks: [{name, passed, message}, ...],
  all_passed: bool,
  gate_level: str
}
```

Gate levels:
- **minimal**: `#lang` header, balanced braces, includes resolve
- **standard**: + test specs exist, behavior files exist, actions have monitors
- **comprehensive**: + manifest exists, coverage > 0, no unguarded state vars

#### ivy_scaffold_check

Check which layers/patterns are present or missing in a protocol model. Compares against the canonical 14-layer decomposition.

```
Parameters:
  protocol: str                            # Protocol name (e.g., "quic", "bgp")

Returns: JSON {
  layers_present: [str, ...],
  layers_missing: [str, ...],
  suggestions: [str, ...],
  completeness_score: float
}
```

### Pattern Library

#### ivy_pattern_analysis

Analyze formal model patterns (serdes, variants, monitors, shims, modules, entities) in a protocol specification.

```
Parameters:
  protocol: str                            # Protocol name
  mode: str = "detect"                     # "detect", "validate", or "compare"
  pattern: str | None = None               # Specific pattern to analyze
  reference_protocol: str | None = None    # Required for "compare" mode

Returns: JSON {
  patterns: [{name, files, instances}, ...],
  total_patterns: int,
  mode: str
}
```

#### ivy_pattern_scaffold

Generate Ivy source code from a pattern template with placeholder substitution.

```
Parameters:
  protocol: str                            # Protocol name for substitution
  pattern: str                             # Pattern: "serdes", "variants", "monitors", "shim", "module", "entity"
  wire_format: str = "binary"              # "binary" or "json" (serdes); "udp" or "tcp" (shim)
  role_type: str = "asymmetric"            # "asymmetric" or "symmetric" (entity)
  variant_names: list[str] | None = None   # Variant/message type names
  roles: list[str] | None = None           # Role names (e.g., ["client", "server"])

Returns: JSON {
  source: str,
  pattern: str,
  file_suggestion: str
}
```

## Recommended Workflows

### Quick Health Check

```
1. ivy_capabilities           # Are tools available?
2. ivy_lint(file)             # Fast structural check (ms)
3. ivy_verify(file)           # Full formal verification (seconds)
```

### Coverage Audit

```
1. ivy_requirement_coverage() # Overall stats
2. ivy_traceability_matrix()  # Detailed per-requirement view
3. ivy_include_graph(file)    # Understand dependency structure
```

### Impact Assessment Before Editing

```
1. ivy_query_symbol(name)     # Understand the symbol
2. ivy_impact_analysis(name)  # What depends on it?
3. ivy_cross_references(id)   # Full neighborhood
4. ivy_verify(file)           # After editing, re-verify
```

### Deep Model Understanding

```
1. ivy_layered_overview(protocol=p)           # Bird's-eye view
2. ivy_model_summary(protocol=p)              # Per-action summary table
3. ivy_action_requirements(action=a)          # Requirements for a specific action
4. ivy_action_dependency_graph(protocol=p)    # How actions relate via shared state
5. ivy_state_machine_view(protocol=p)         # FSM perspective
```

### New Protocol Scaffolding

```
1. ivy_scaffold_check(protocol=p)             # What's missing?
2. ivy_pattern_analysis(protocol=ref, mode="detect")  # Detect patterns in reference
3. ivy_pattern_scaffold(protocol=p, pattern="serdes")  # Generate from template
4. ivy_quality_gate(protocol=p, gate_level="minimal")  # Validate basics
```

### Thorough Diagnostics After Editing

```
1. ivy_lint(file)                             # Fast structural check (ms)
2. ivy_diagnostics(file)                      # Full 5-layer diagnostic analysis
3. ivy_smart_suggestions(file_path=f)         # Improvement suggestions
4. ivy_verify(file)                           # Formal verification
```

### RFC Manifest Generation

```
1. ivy_extract_requirements(rfc_text)         # Parse normative statements
2. ivy_generate_manifest(rfc_name, rfc_text)  # Generate YAML manifest
3. ivy_requirement_coverage()                 # Check current coverage
4. ivy_coverage_gaps(protocol=p)              # Find specific gaps
```

## Integration

**Related skills:**
- **panther-ivy:ivy-tooling-guide** — High-level tooling architecture
- **panther-ivy:ivy-lsp-navigation** — LSP-specific tool patterns

**Related agents:**
- **spec-verifier** — Uses these tools for verification
- **traceability-reviewer** — Uses coverage/traceability tools
