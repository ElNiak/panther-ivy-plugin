---
name: Ivy Tooling Guide
description: This skill should be used when the user asks about "Ivy tool guidance", "how to check Ivy files", "how to compile Ivy", "formal verification tools", "ivy_check alternative", "MCP tools for Ivy", "Ivy LSP", "Ivy diagnostics", or mentions any Ivy toolchain operation in the PANTHER framework. Provides the architecture of native LSP + ivy-tools MCP, tool mapping from CLI to MCP equivalents, and correct usage patterns.
---

# Ivy Tooling Guide

## Architecture

The panther-ivy-plugin provides Ivy code intelligence through two complementary layers:

| Layer | Role | How it works |
|-------|------|-------------|
| **Native Ivy LSP** | Real-time code intelligence | Claude Code runs ivy_lsp as a language server — diagnostics, go-to-definition, find-references, hover, and document symbols are available automatically for `.ivy` files |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_lsp runs in MCP mode (`--mcp`) providing structured tool access to ivy_verify, ivy_compile, ivy_model_info, ivy_lint, and more |

For code navigation and editing, use Claude's built-in tools (`Read`, `Edit`, `Write`, `Grep`, `Glob`). The native LSP enriches these with Ivy-specific intelligence.

## What Claude Gets Automatically from LSP

When editing `.ivy` files, Claude receives:

- **Instant diagnostics** — Parse errors, missing includes, structural warnings appear immediately after each edit
- **Go-to-definition** — Jump to symbol definitions across `include` boundaries
- **Find-references** — Locate all usages of a symbol across the workspace
- **Hover** — Type signatures and documentation for symbols
- **Document symbols** — File outline with nested hierarchy of types, objects, actions, modules

No MCP tool calls needed — this is built into Claude Code's edit loop.

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

1. **Navigate** — Use `Read`, `Grep`, `Glob` to locate relevant code. LSP provides go-to-definition and find-references automatically.
2. **Understand** — Use `Read` to examine implementations. LSP hover provides type signatures and documentation.
3. **Edit** — Use `Edit` for modifications, `Write` for new files. LSP shows diagnostics immediately after each edit.
4. **Verify** — Use ivy-tools MCP tools (`ivy_verify`, `ivy_compile`) to confirm formal properties hold.

### Example: Adding a New Requirement

```
1. Grep for "frame.stream.handle" to find where stream handling is defined
2. Read the file to understand the current implementation
3. Grep for references to the symbol across the workspace
4. Edit the file to add a new before/after monitor
5. Use ivy_verify MCP tool to verify consistency
```

## Enforcement

The panther-ivy-plugin includes a PreToolUse hook that blocks direct Ivy CLI calls in Bash. If a Bash command containing `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` is attempted, the hook rejects it with a message directing to the ivy-tools MCP equivalents.

Use `/nct-check`, `/nct-compile`, and `/nct-model-info` commands as convenient shortcuts for the most common operations.

## Prerequisites

- **ivy_lsp** available — installed via `pip install ivy-lsp` or accessible via `uvx --from git+https://github.com/ElNiak/ivy-lsp`
- **Ivy toolchain** available in PATH for verification operations (ivy_check, ivyc, ivy_show)
