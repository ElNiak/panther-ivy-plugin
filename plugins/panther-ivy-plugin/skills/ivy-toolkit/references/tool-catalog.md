# Ivy-Tools MCP Tool Catalog

Complete parameter documentation for all ivy-tools MCP server tools. This is the
single source of truth -- all other skills reference this file.

All ivy-tools MCP tools follow this prefix: `mcp__plugin_panther-ivy-plugin_ivy-tools__<tool_name>`

## Verification and Linting

### ivy_verify
Run `ivy_check` on an Ivy file. Returns structured diagnostics.
```
Parameters:
  relative_path: str           # Path to .ivy file (relative to project root)
  isolate: str | None = None   # Optional isolate name

Returns: { success, diagnostics, diagnostic_count, raw_output, duration_seconds }
```
Timeout: 120 seconds.

### ivy_compile
Compile an Ivy file to a test executable using `ivyc`.
```
Parameters:
  relative_path: str           # Path to .ivy file
  target: str = "test"         # Compilation target
  isolate: str | None = None   # Optional isolate name

Returns: { success, output, duration_seconds }
```
Timeout: 300 seconds.

### ivy_model_info
Display model structure using `ivy_show`.
```
Parameters:
  relative_path: str           # Path to .ivy file
  isolate: str | None = None   # Optional isolate name

Returns: { success, output, duration_seconds }
```
Timeout: 30 seconds.

### ivy_diagnostics
Diagnostic analysis with two modes: `mode="structural"` for fast structural lint (milliseconds, no subprocess), or `mode="full"` for 5-layer analysis (structural, lexer, semantic, coverage, pattern). Defaults to full analysis if mode is omitted.
```
Parameters:
  relative_path: str
  layers: list[str] | None = None       # Optional: structural, lexer, semantic, coverage, pattern
  min_severity: str | None = None       # Optional: error, warning, info, hint

Returns: { diagnostics, diagnostic_count, by_layer }
```

## Dependency Analysis

### ivy_include_graph
Return include dependency graph for Ivy files.
```
Parameters:
  relative_path: str | None = None      # Optional file to focus on

Returns (focused): { file, includes, included_by, transitive_includes }
Returns (full): { files, total_files }
```

### ivy_capabilities
Check which Ivy CLI tools are available on PATH.
```
Parameters: none
Returns: { ivy_check, ivyc, ivy_show }
```

## Coverage and Traceability

### ivy_coverage
Consolidated coverage tool with three modes.
```
Parameters:
  mode: str                    # "stats" | "gaps" | "matrix"
  relative_path: str | None    # Path to .ivy file or directory (stats, matrix modes)
  test_file: str | None        # Path to test .ivy file (gaps mode, optional for stats/matrix)
  protocol: str | None         # Protocol name (gaps mode)

Mode "stats": Coverage statistics by MUST/SHOULD/MAY level and layer
Returns: { total, covered, uncovered, coverage_percent, by_level, by_layer }

Mode "gaps": Identify unguarded state vars, uncovered requirements, orphaned monitors
Returns: { unguarded_state_vars, uncovered_requirements, orphaned_monitors, gap_count }

Mode "matrix": RFC requirement-to-annotation mapping
Returns: { total_requirements, covered, uncovered, matrix }
```

## Semantic Query (Removed -- Use LSP)

`ivy_query` has been removed. Its capabilities are now provided by the Ivy LSP server:
- **Symbol info** (was `ivy_query(mode="info")`): Use LSP `hover` for type info and docs
- **Impact analysis** (was `ivy_query(mode="impact")`): Use LSP `incomingCalls`/`outgoingCalls` for call edges
- **Cross-references** (was `ivy_query(mode="xrefs")`): Use LSP `findReferences` for all usages

## RFC Extraction

### ivy_extract_requirements
Parse RFC text for normative statements (MUST/SHOULD/MAY). With output="manifest", generates a YAML requirements manifest.
```
Parameters:
  rfc_text: str                # RFC text to parse
  output: str = "structured"   # "structured" | "manifest"
  rfc_name: str | None = None  # RFC identifier (required for output="manifest")

Default (output="structured"):
Returns: { requirements, total, by_level }

With output="manifest":
Returns: { yaml, total_requirements, suggested_path, by_level }
```

## Model Visualization

### ivy_visualize
Consolidated visualization tool with three views.
```
Parameters:
  view: str                    # "dependencies" | "state_machine" | "layers"
  test_file: str               # Path to test .ivy file

View "dependencies": Action dependency graph via shared state
Returns: { nodes, edges, total_actions }

View "state_machine": State-machine perspective of the model
Returns: { states, transitions, total_states }

View "layers": Layered overview organized by file or module
Returns: { layers, total_files }
```

### ivy_model_summary
Consolidated model summary tool with two detail levels.
```
Parameters:
  detail: str = "summary"      # "summary" | "requirements"
  test_file: str | None = None # Path to test .ivy file
  action_name: str | None = None  # Action name (for detail="requirements")
  file_path: str | None = None    # File path (for detail="requirements")

Detail "summary": Per-action requirement counts, state variable usage, RFC coverage
Returns: { rows, total_actions }

Detail "requirements": Requirements organized by action boundaries (before/after monitors)
Returns: { actions, total_actions }
```

## Quality

### ivy_quality
Consolidated quality tool with two modes.
```
Parameters:
  mode: str                    # "suggestions" | "gate"
  file_path: str | None = None # Path to .ivy file (suggestions mode)
  protocol: str | None = None  # Protocol name (gate mode)
  gate_level: str = "minimal"  # "minimal" | "standard" | "comprehensive" (gate mode)

Mode "suggestions": Context-aware suggestions for improving a specification. Note: file_path/line/context parameters currently have no effect on output (known issue).
Returns: { suggestions, total }

Mode "gate": Validate a protocol model against quality gates.
Returns: { checks, all_passed, gate_level }
```

## Pattern Analysis

### ivy_patterns
Consolidated pattern analysis tool with four modes.
```
Parameters:
  mode: str                    # "analyze" | "validate" | "compare" | "check"
  protocol: str                # Protocol name (e.g., "quic", "bgp")
  pattern: str | None = None   # Optional specific pattern (e.g., "serdes", "variants")
  reference_protocol: str | None = None  # Required for "compare" mode

Mode "analyze": Analyze formal model patterns in a specification
Returns: { patterns, total_patterns, mode }

Mode "validate": Cross-reference validation of detected patterns
Returns: { patterns, issues, validation_summary }

Mode "compare": Compare patterns between two protocols (requires reference_protocol)
Returns: { protocol_a, protocol_b, comparison }

Mode "check": Check which layers/patterns are present or missing
Returns: { layers_present, layers_missing, suggestions, completeness_score }
```

### ivy_pattern_scaffold
Generate Ivy source code from a pattern template.
```
Parameters:
  protocol: str                # Protocol name
  pattern: str                 # Pattern type to scaffold

Returns: { source, pattern, file_suggestion }
```
