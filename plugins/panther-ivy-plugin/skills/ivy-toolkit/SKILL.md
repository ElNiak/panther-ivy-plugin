---
name: ivy-toolkit
description: "Use when choosing which Ivy tool to use, looking up MCP tool parameters,
  or needing guidance on tool selection for Ivy tasks. Single source of truth for all
  ivy-tools MCP tool documentation."
---

# Ivy Toolkit

Single source of truth for Ivy tool operations. All skills and commands reference this
skill instead of maintaining their own tool documentation.

## Iron Law

**NEVER invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` directly via Bash.**
ALWAYS use the ivy-tools MCP equivalents. The PreToolUse hook enforces this, but
you should know it proactively.

## Tool Architecture

Three complementary tool systems:

| System | Purpose | Examples |
|--------|---------|---------|
| **Native Ivy LSP** | Navigation, diagnostics, go-to-definition | documentSymbol, definition, references, hover |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_verify, ivy_compile, ivy_model_info, ivy_lint |
| **Claude native tools** | File I/O, search, editing | Read, Write, Edit, Grep, Glob |

**Workflow:** Navigate (LSP) -> Understand (LSP+MCP) -> Edit (Claude) -> Verify (MCP)

## Quick Tool Reference

| MCP Tool | Purpose | When to Use | Mode |
|----------|---------|-------------|------|
| `ivy_verify` | Formal verification | After writing/modifying specs | FAST + DEEP |
| `ivy_compile` | Compile to test binary | After verification passes | FAST + DEEP |
| `ivy_model_info` | Show model structure | Understanding a spec file | FAST |
| `ivy_lint` | Fast pattern checks | Before full verification | FAST + DEEP |
| `ivy_diagnostics` | Full 5-layer diagnostics | Deep structural analysis | DEEP |
| `ivy_include_graph` | Show include dependencies | Phase 1 exploration | DEEP |
| `ivy_capabilities` | Check server capabilities | Diagnostics | FAST |
| `ivy_coverage` | Requirement coverage stats | Phase 1 + Phase 5 | DEEP |
| `ivy_query` | Query symbol information | Navigation | FAST |
| `ivy_extract_requirements` | Extract RFC requirements | Phase 2 planning | DEEP |
| `ivy_visualize` | Dependency visualization | Understanding architecture | FAST |
| `ivy_model_summary` | Summarize model | Quick overview | FAST |
| `ivy_patterns` | Detect formal patterns | Pattern analysis | FAST |
| `ivy_pattern_scaffold` | Generate from template | Scaffolding new specs | FAST |
| `ivy_quality` | Quality score | Phase 4 verification | DEEP |

## Mode Mapping

**FAST mode tools** -- safe for single-operation commands (/nct-check, /nct-model-info):
- ivy_verify, ivy_compile, ivy_model_info, ivy_lint, ivy_capabilities, ivy_query,
  ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold

**DEEP mode tools** -- used during orchestrated workflows (ivy-workflow-orchestrator):
- ivy_diagnostics (full analysis), ivy_include_graph (Phase 1),
  ivy_coverage (Phase 1+5), ivy_extract_requirements (Phase 2),
  ivy_quality (Phase 4)
- All FAST tools are also available in DEEP mode

## LSP Operations

The Ivy LSP provides these operations through the native LSP tool:

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

## Coverage Tool Scoping

The `ivy_coverage` tool accepts different scoping parameters:

| Parameter | Scoping Semantics | Use When |
|---|---|---|
| `relative_path` | Directory-prefix filtering | Browsing a subdirectory |
| `test_file` | Endpoint-mirror scoping (transitive include closure) | NCT-aligned per-endpoint coverage |
| `protocol` | Directory-prefix `protocol-testing/{protocol}/` | Filtering by protocol |

**Recommendation**: Use `test_file` for accurate NCT-aligned results.

## Enforcement

- The **PreToolUse hook** (`block-direct-ivy.sh`) intercepts direct CLI invocations
- If blocked, use the MCP equivalent from the table above
- The hook provides a helpful redirect message with the correct MCP tool name

## Reference Files

- **references/tool-catalog.md** -- Full parameter documentation, outputs, and examples for every MCP tool

## Integration

- **LOADED BY:** ivy-workflow-orchestrator (all phases), all methodology skills
- **REPLACES:** Duplicated tool sections in methodology-reference, nct-methodology, workflow-reference, incremental-spec-dev, tooling-reference
