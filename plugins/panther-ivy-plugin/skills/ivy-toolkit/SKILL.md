---
name: ivy-toolkit
description: "22-tool MCP catalog with parameter matrix and selection guide. Use when choosing or invoking MCP tools for Ivy operations."
user-invocable: false
allowed-tools: "Read Grep Glob ToolSearch"
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
| **ivy-tools MCP** | Verification, compilation, analysis | ivy_verify, ivy_compile, ivy_model_info, ivy_diagnostics |
| **Claude native tools** | File I/O, search, editing | Read, Write, Edit, Grep, Glob |

**Workflow:** Navigate (LSP) -> Understand (LSP+MCP) -> Edit (Claude) -> Verify (MCP)

## Quick Tool Reference

| MCP Tool | Purpose | When to Use | Mode |
|----------|---------|-------------|------|
| `ivy_verify` | Formal verification | After writing/modifying specs | FAST + DEEP |
| `ivy_compile` | Compile to test binary | After verification passes | FAST + DEEP |
| `ivy_model_info` | Show model structure | Understanding a spec file | FAST |
| `ivy_diagnostics` | Structural check (mode="structural") or full 5-layer (mode="full") | Before full verification / deep analysis | FAST + DEEP |
| `ivy_include_graph` | Show include dependencies | Phase 1 exploration | DEEP |
| `ivy_capabilities` | Check server capabilities | Diagnostics | FAST |
| `ivy_coverage` | Requirement coverage stats | Phase 1 + Phase 5 | DEEP |
| `ivy_extract_requirements` | Extract RFC requirements | Phase 2 planning | DEEP |
| `ivy_visualize` | Dependency visualization | Understanding architecture | FAST |
| `ivy_model_summary` | Summarize model | Quick overview | FAST |
| `ivy_patterns` | Detect formal patterns | Pattern analysis | FAST |
| `ivy_pattern_scaffold` | Generate from template | Scaffolding new specs | FAST |
| `ivy_quality` | Quality score | Phase 4 verification | DEEP |
| `ivy_health_check` | Server health status | Pre-flight check before tool use | FAST |
| `ivy_scope` | Show workspace scope for a protocol | Workspace management | FAST |
| `ivy_index` | Index protocol files into workspace | Workspace initialization | FAST |
| `ivy_manifest` | Show/generate protocol manifest | Protocol inventory | FAST |
| `ivy_verification_dashboard` | Overview of verification state | Phase 4 reporting | DEEP |
| `ivy_find_variants` | Find all variants of a type | Type analysis | FAST |
| `ivy_serdes_correlation` | Correlate serializer/deserializer for a type | Ser/des analysis | FAST |
| `ivy_change_impact` | Assess impact of changing a type | Change analysis | DEEP |

## Mode Mapping

**FAST mode tools** -- safe for single-operation commands (/nct-check, /nct-model-info):
- ivy_verify, ivy_compile, ivy_model_info, ivy_diagnostics(mode="structural"), ivy_capabilities,
  ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold

**DEEP mode tools** -- used during orchestrated workflows (build, verify, review):
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

> **Workspace**: For accurate scoping, first activate the workspace with `/set-workspace <protocol>`. All tool paths are workspace-relative.

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

### Tool Selection Decision Matrix

*(Merged from tooling-reference)*

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

### Coordination Workflows

### Workflow A: Understanding a Symbol Fully
1. `workspaceSymbol` -- find the symbol by name
2. `goToDefinition` -- read its full definition
3. `hover` -- get type signature and docs
4. `findReferences` -- see all usages across workspace
5. LSP `incomingCalls`/`outgoingCalls` -- see incoming/outgoing call edges

### Workflow B: Adding a New Requirement Monitor
1. `documentSymbol` or `workspaceSymbol` -- find the relevant action
2. `findReferences` -- find existing before/after monitors
3. `Read` -- read the existing monitors to understand the pattern
4. MCP `ivy_coverage` (mode="stats") -- check what requirements are missing
5. `Edit` -- write the new monitor with bracket tag
6. MCP `ivy_diagnostics(mode="structural")` -- fast structural check after edit
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

---

See [references/lsp-patterns.md](references/lsp-patterns.md) for LSP invocation patterns and coordination examples.

## Reference Files

- **references/tool-catalog.md** -- Full parameter documentation, outputs, and examples for every MCP tool

## Integration

- **LOADED BY:** All workflow skills and agents
- **SUPERSEDES:** Duplicated tool sections previously in methodology-reference and other deleted skills (merged from tooling-reference)
