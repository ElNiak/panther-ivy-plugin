---
name: knowledge-ivy-toolkit
description: "Use when choosing or invoking MCP tools for Ivy operations. Provides the 18-tool ivy-tools catalog plus Serena semantic tools, with parameter matrix, mode map, and selection guide."
user-invocable: false
---

# Ivy Toolkit

**Type:** flexible — adapt principles to context.

Single source of truth for Ivy tool operations. All skills and commands reference this skill instead of maintaining their own tool documentation.

## Iron Law

**NEVER invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` directly via Bash.** ALWAYS use the ivy-tools MCP equivalents. The PreToolUse hook (`hooks/scripts/block-direct-ivy.sh`) warns about direct CLI invocations and suggests the MCP equivalent (exit 0, informational); follow the rule proactively.

## Tool Architecture

Three complementary tool systems plus Claude's native tools:

| System | Purpose | Examples |
|--------|---------|----------|
| **Native Ivy LSP** | Navigation, diagnostics, go-to-definition | documentSymbol, definition, references, hover |
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_verify, ivy_compile, ivy_model_info, ivy_diagnostics |
| **serena MCP** | Semantic symbol search, rename, refactor, session memory | find_symbol, find_referencing_symbols, rename_symbol, replace_symbol_body |
| **Claude native** | File I/O, search, editing | Read, Write, Edit, Grep, Glob |

**Workflow:** Navigate (LSP) → Understand (LSP + MCP) → Edit (Claude) → Verify (MCP)

## Quick Tool Reference

| MCP Tool | Purpose | When to Use | Mode |
|----------|---------|-------------|------|
| `ivy_verify` | Formal verification | After writing / modifying specs | FAST + DEEP |
| `ivy_compile` | Compile to test binary | After verification passes | FAST + DEEP |
| `ivy_model_info` | Show model structure | Understanding a spec file | FAST |
| `ivy_diagnostics` | Structural (`mode="structural"`), full 5-layer (`mode="full"`), dashboard (`mode="dashboard"`), or cross-workspace collisions (`mode="collisions"`) | Before full verification / deep analysis / Phase 4 reporting / include-graph triage | FAST + DEEP |
| `ivy_analysis` | Include dependencies (`mode="includes"`) or workspace scope (`mode="scope"`) | Phase 1 exploration / workspace management | FAST + DEEP |
| `ivy_status` | Capabilities (`mode="capabilities"`) or health (`mode="health"`) | Pre-flight check / diagnostics | FAST |
| `ivy_coverage` | Requirement coverage stats | Phase 1 + Phase 5 | DEEP |
| `ivy_extract_requirements` | Extract RFC requirements | Phase 2 planning | DEEP |
| `ivy_visualize` | Dependencies / state machine / layers / summary / requirements | Understanding architecture, quick overview | FAST |
| `ivy_patterns` | Detect formal patterns; `mode="scaffold"` generates from template | Pattern analysis, scaffolding new specs | FAST |
| `ivy_quality` | Quality score | Phase 4 verification | DEEP |
| `ivy_index` | Index protocol files into workspace | Workspace initialization | FAST |
| `ivy_manifest` | Show / generate protocol manifest | Protocol inventory | FAST |
| `ivy_propagation` | Type propagation — variants, serdes correlation, change impact | Type analysis, ser/des analysis, change analysis | FAST + DEEP |
| `ivy_rfc` | RFC lookup, search, and normative analysis (`mode=get/search/section`) | RFC operations during spec authoring | FAST |
| `ivy_workspace` | Activate, inspect, clear protocol workspace scoping (`action=set/get/list/clear`) | Workspace management and cross-protocol isolation | FAST |
| `ivy_workflow_state` | Read / append the active-workflow flag and per-workflow journal | Workflow phase transitions, journal writes | FAST |
| `ivy_iut_test` | Execute a compiled test binary against a real IUT via PANTHER | End-to-end IUT runs during verify workflow | DEEP |

## Mode Mapping

**FAST mode tools** — safe for single-operation commands (`/nct-check`, `/nct-model-info`):
`ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_diagnostics(mode="structural")`, `ivy_status`, `ivy_visualize`, `ivy_patterns`, `ivy_rfc`.

**DEEP mode tools** — used during orchestrated workflows (build, verify, review):
`ivy_diagnostics` (full analysis), `ivy_analysis(mode="includes")` (Phase 1), `ivy_coverage` (Phase 1 + 5), `ivy_extract_requirements` (Phase 2), `ivy_quality` (Phase 4).

All FAST tools are also available in DEEP mode.

## Coverage Tool Scoping

> **Workspace**: For accurate scoping, first activate the workspace with `/set-workspace <protocol>`. All tool paths are workspace-relative.

`ivy_coverage` accepts these scoping parameters:

| Parameter | Scoping Semantics | Use When |
|---|---|---|
| `relative_path` | Directory-prefix filtering | Browsing a subdirectory |
| `test_file` | Endpoint-mirror scoping (transitive include closure) | NCT-aligned per-endpoint coverage |
| `protocol` | Directory-prefix `protocol-testing/{protocol}/` | Filtering by protocol |

**Recommendation**: use `test_file` for accurate NCT-aligned results.

## Reference dispatch

| When | Read |
|---|---|
| Per-tool parameters, errors, tiers, rendering | `references/tool-catalog.md` |
| Cross-cutting MCP error patterns and recovery | `references/error-reference.md` |
| Performance tiers, timeouts, concurrency model | `references/timing-and-concurrency.md` |
| Tool invocation pipeline and rendering rules | `references/hook-lifecycle.md` |
| LSP operations table + multi-tool coordination workflows + tool-selection decision matrix | `references/lsp-coordination.md` |
| LSP scoping policy and per-operation usage notes | `references/lsp-patterns.md` |
| Canonical multi-line invocation shapes for `ivy_diagnostics`, `ivy_verify`, `ivy_propagation`, `ivy_iut_test`, `ivy_compile` | `references/tool-invocation-examples.md` |

## Serena MCP

Serena runs as a second MCP server (registered in `.mcp.json` alongside ivy-tools, gated on `PANTHER_IVY_ENABLE_SERENA`). It provides semantic symbol operations that complement Ivy LSP navigation with cross-file refactoring and session memory.

**When to prefer Serena over ivy-tools MCP:** cross-file refactoring, symbol renaming, or session memory. For verification / compilation / coverage / RFC lookup, prefer the ivy-tools MCP table above. For Serena's per-tool inventory (`find_symbol`, `find_referencing_symbols`, `get_symbols_overview`, `rename_symbol`, `replace_symbol_body`, `insert_*_symbol`, `search_for_pattern`, the LSP wrappers, and the session-memory tools), see `references/lsp-coordination.md` or the `.mcp.json` configuration.

## Integration

- **Loaded by:** all workflow skills and agents.
- **Supersedes:** duplicated tool sections previously in methodology-reference and other deleted skills (merged from tooling-reference).
