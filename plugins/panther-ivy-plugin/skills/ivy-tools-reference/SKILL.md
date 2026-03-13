---
name: Ivy Tools Reference (Diagnostics)
description: Use when asking about "ivy diagnostics", "ivy lint", "ivy verification",
  "ivy coverage", "ivy traceability", "ivy include graph", "ivy capabilities",
  "ivy impact analysis", "ivy requirements", "ivy cross references", "ivy query symbol",
  or any read-only Ivy analysis task. Provides tool mapping for the ivy-tools MCP server.
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
