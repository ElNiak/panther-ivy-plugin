---
name: ivy-toolkit
description: "Use when choosing or invoking MCP tools for Ivy operations. Provides the 18-tool ivy-tools catalog plus Serena semantic tools, with parameter matrix, mode map, and selection guide."
user-invocable: false
---

# Ivy Toolkit

**Type:** flexible — adapt principles to context.

**Journal:** read-only knowledge skill. Per `.claude/rules/journaling-contract.md` §1, this skill does NOT write to `.panther-ivy/workflow-journal.yaml`; the orchestrator and the 5 ops-skills are the writer surfaces.

Single source of truth for Ivy tool operations. All skills and commands reference this skill instead of maintaining their own tool documentation. Three complementary tool systems are available: native Ivy LSP (navigation, diagnostics, go-to-definition), the ivy-tools MCP (verification, compilation, analysis), the Serena MCP (semantic symbol search, rename, refactor, session memory), plus Claude's native tools for file I/O and editing. The standard workflow is Navigate (LSP) → Understand (LSP + MCP) → Edit (Claude) → Verify (MCP).

## Iron Law

**NEVER invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` directly via Bash.** ALWAYS use the ivy-tools MCP equivalents. The PreToolUse hook (`hooks/scripts/block-direct-ivy.sh`) warns about direct CLI invocations and suggests the MCP equivalent (exit 0, informational); follow the rule proactively.

## Serena MCP

Serena runs as a second MCP server (registered in `.mcp.json` alongside ivy-tools, gated on `PANTHER_IVY_ENABLE_SERENA`). It provides semantic symbol operations that complement Ivy LSP navigation with cross-file refactoring and session memory. Prefer Serena for cross-file refactoring, symbol renaming, or session memory; prefer the ivy-tools MCP for verification / compilation / coverage / RFC lookup. Serena's per-tool inventory (`find_symbol`, `find_referencing_symbols`, `get_symbols_overview`, `rename_symbol`, `replace_symbol_body`, `insert_*_symbol`, `search_for_pattern`, the LSP wrappers, the session-memory tools) is in `references/lsp-coordination.md` and `.mcp.json`.

## References

- `references/tool-catalog.md` — per-tool reference (parameters, returns, timeout, tier, rendering, errors, when-to-use) for all 18 ivy-tools MCP tools, plus the Quick Tool Reference summary table, the FAST/DEEP mode mapping, and the `ivy_coverage` scoping decision table (`relative_path` / `test_file` / `protocol`).
- `references/error-reference.md` — cross-cutting MCP error patterns and recovery procedures.
- `references/timing-and-concurrency.md` — performance tiers, timeouts, and the concurrency model (semaphores, in-flight dedup).
- `references/hook-lifecycle.md` — tool invocation pipeline and rendering rules (`render-tool-result.py` post-processing).
- `references/lsp-coordination.md` — LSP operations table, multi-tool coordination workflows, and the tool-selection decision matrix.
- `references/lsp-patterns.md` — LSP scoping policy and per-operation usage notes.
- `references/tool-invocation-examples.md` — canonical multi-line invocation shapes for `ivy_diagnostics`, `ivy_verify`, `ivy_propagation`, `ivy_iut_test`, `ivy_compile`.

## Integration

- **Loaded by:** all workflow skills and agents.
- **Supersedes:** duplicated tool sections previously in methodology and other deleted skills (merged from tooling-reference).
