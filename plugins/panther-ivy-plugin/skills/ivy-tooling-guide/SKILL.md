---
name: ivy-tooling-guide
description: Use when choosing between LSP, MCP tools, and Claude native tools for an Ivy task, or when confused about the tooling architecture
---

# Ivy Tooling Guide

## Architecture

The panther-ivy-plugin provides Ivy code intelligence through two complementary layers:

| Layer | Role | How it works |
|-------|------|-------------|
| **Native Ivy LSP** | Code intelligence via LSP tool | Claude Code runs ivy_lsp as a language server — go-to-definition, find-references, hover, and document symbols are available via the `LSP` tool for `.ivy` files |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_lsp runs in MCP mode (`--mcp`) providing structured tool access to ivy_verify, ivy_compile, ivy_model_info, ivy_lint, and more |

For code navigation and editing, use Claude's built-in tools (`Read`, `Edit`, `Write`, `Grep`, `Glob`). The native LSP enriches these with Ivy-specific intelligence.

## What Claude Gets from the LSP Tool

Use the `LSP` tool explicitly for `.ivy` file navigation:

- **Go-to-definition** — Jump to symbol definitions across `include` boundaries
- **Find-references** — Locate all usages of a symbol across the workspace
- **Hover** — Type signatures and documentation for symbols
- **Document symbols** — File outline with nested hierarchy of types, objects, actions, modules
- **Workspace symbols** — Search for symbols by name across all `.ivy` files

**Important**: Claude Code does NOT receive automatic diagnostics (`textDocument/publishDiagnostics` is not supported). Use MCP `ivy_lint` and `ivy_diagnostics` for error checking after edits. See the `ivy-lsp-navigation` skill for detailed invocation patterns.

## What Requires MCP Tools

Verification, compilation, and analysis require explicit ivy-tools MCP calls:

### Tool Mapping: CLI → ivy-tools MCP

| Direct CLI Command | MCP Tool | Usage |
|---|---|---|
| `ivy_check file.ivy` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` | Formal verification |
| `ivyc target=test file.ivy` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` | Test compilation |
| `ivy_show file.ivy` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` | Model introspection |
| Fast structural lint | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` | No subprocess, ms |
| Include dependency graph | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` | Show file dependencies |
| Tool availability check | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` | Check what's available |
| RFC coverage matrix | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_traceability_matrix` | Requirement traceability |
| Coverage statistics | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_requirement_coverage` | Coverage stats by level |
| Symbol edge analysis | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_impact_analysis` | Impact analysis |
| Parse RFC statements | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_extract_requirements` | Normative statement extraction |
| Graph neighborhood | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_cross_references` | Symbol graph queries |
| Rich symbol info | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query_symbol` | Detailed symbol information |
| Full 5-layer diagnostics | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` | Thorough analysis (structural, lexer, semantic, coverage, pattern) |
| Generate requirements manifest | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_generate_manifest` | YAML manifest from RFC text |
| Requirements by action | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_action_requirements` | Before/after monitors grouped by action |
| Per-action summary table | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_summary` | Counts, state vars, RFC tags per action |
| Coverage gap analysis | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage_gaps` | Unguarded vars, uncovered requirements |
| Action dependency graph | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_action_dependency_graph` | Shared-state relationships between actions |
| State machine view | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_state_machine_view` | FSM perspective of specification |
| Layered overview | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_layered_overview` | Model organized by file or module |
| Smart suggestions | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_smart_suggestions` | Context-aware improvement suggestions |
| Pattern detection | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_pattern_analysis` | Detect/validate/compare protocol patterns |
| Pattern scaffolding | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_pattern_scaffold` | Generate Ivy source from pattern templates |
| Layer completeness check | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_scaffold_check` | Check 14-layer decomposition completeness |
| Quality gate validation | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_quality_gate` | Validate against minimal/standard/comprehensive gates |

For full parameter documentation, see the `ivy-tools-reference` skill.

## Code Navigation and Editing

Use Claude's built-in tools for all code navigation and editing:

| Operation | Tool | Notes |
|---|---|---|
| Read file contents | `Read` | Read any `.ivy` file directly |
| Search across files | `Grep` | Regex search across the workspace |
| Find files by pattern | `Glob` | Find `.ivy` files by name/path pattern |
| Edit symbol bodies | `Edit` | Modify code in place |
| Create new `.ivy` files | `Write` | Create new specification files |
| List directory contents | `Glob` or `Bash` (ls) | Explore protocol structure |

The native Ivy LSP enhances these with semantic understanding — go-to-definition navigates across `include` boundaries, find-references traces symbol usage, and hover shows type information.

## Recommended Workflow

### Navigate → Understand → Edit → Verify

1. **Navigate** — Use LSP `documentSymbol` and `workspaceSymbol` to find symbols, `goToDefinition` to follow references across includes, `findReferences` to trace usages. Fall back to `Grep` for regex patterns.
2. **Understand** — Use LSP `hover` for type signatures. Use `Read` to examine full implementations.
3. **Edit** — Use `Edit` for modifications, `Write` for new files. Run MCP `ivy_lint` after edits (also runs automatically via post-write hook).
4. **Verify** — Use ivy-tools MCP tools (`ivy_verify`, `ivy_compile`) to confirm formal properties hold.

### Example: Adding a New Requirement

```
1. LSP `workspaceSymbol` to find "frame.stream.handle" across workspace
2. LSP `goToDefinition` to jump to its definition
3. LSP `findReferences` to find all existing monitors for this action
4. Read the monitors to understand the pattern
5. Edit the behavior file to add a new before/after monitor with bracket tag
6. `ivy_lint` runs automatically (post-write hook)
7. Use `ivy_verify` MCP tool to verify consistency
```

## Enforcement

The panther-ivy-plugin includes a PreToolUse hook that blocks direct Ivy CLI calls in Bash. If a Bash command containing `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` is attempted, the hook rejects it with a message directing to the ivy-tools MCP equivalents.

Use `/nct-check`, `/nct-compile`, and `/nct-model-info` commands as convenient shortcuts for the most common operations.

## Prerequisites

- **ivy_lsp** available — installed via `pip install ivy-lsp` or accessible via `uvx --from git+https://github.com/ElNiak/ivy-lsp`
- **Ivy toolchain** available in PATH for verification operations (ivy_check, ivyc, ivy_show)

## Integration

**Related skills:**
- **panther-ivy:ivy-tools-reference** — Detailed tool parameters and return types
- **panther-ivy:ivy-lsp-navigation** — LSP-specific decision matrix
- **panther-ivy:ivy-lsp-walkthrough** — End-to-end tooling example
