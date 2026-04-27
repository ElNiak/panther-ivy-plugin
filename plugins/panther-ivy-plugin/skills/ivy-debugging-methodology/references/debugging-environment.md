# Debugging Environment

This reference covers content unique to debugging flows: the agent self-evaluation loop,
debug environment variables, and LSP indexing awareness.

## Canonical 9-step runbook

The full 9-step Ivy LSP + MCP health-check runbook (log file paths, common failures,
process liveness, workspace access, cross-file resolution) lives in the triage skill.
When a debugging session needs a full diagnostic, dispatch the triage skill via
`Skill(skill="panther-ivy-plugin:triage")` (direct mode) — it owns the canonical
runbook. This file does not duplicate that runbook.

## Agent Self-Evaluation Protocol

After writing or modifying Ivy specifications, run this verification loop:

1. **`ivy_diagnostics(mode="structural")`** — Fast structural check (milliseconds). Fix: missing `#lang`, unresolved includes, unmatched braces.
2. **`ivy_verify`** — Formal property verification. If FAIL: read error line → locate with Grep/LSP go-to-definition → diagnose (missing invariant? action bug? missing precondition?) → fix → re-verify.
3. **`ivy_coverage`** (mode="stats") — Check MUST requirement coverage. If low, add missing `before`/`after` monitors with bracket tags.
4. **`ivy_coverage`** (mode="matrix") — Review assertion-to-requirement mapping. Add bracket tags (`# [rfcNNNN:X.Y]`) to uncovered assertions.
5. **Anti-pattern checklist** — before declaring work complete:
   - Missing `after init` → relations/functions start with arbitrary values, not defaults
   - Ungrounded variables in invariants → `invariant sent(P, N)` means "for ALL P and N, sent is true"
   - `assume` instead of `require` → weakens the model unsoundly, use `require` for preconditions
   - Missing `require` in `before` clauses → actions become callable in any state
   - Circular include dependencies → Ivy does not support circular includes, structure as DAG
   - Forgetting to `export _finalize` → end-state checks will not execute

## Debug environment variables

- `IVY_LSP_LOG_LEVEL=DEBUG` — verbose logging
- `IVY_LSP_FORCE_REINSTALL=1` — force `uvx` to reinstall the package (not set by default; use when modifying local ivy-lsp source)
- `IVY_LSP_DEV_ROOT=/path/to/local/ivy-lsp` — use local development copy
- `PANTHER_IVY_ENABLE_SERENA=1` — enable the Serena MCP server (disabled by default; requires panther-serena submodule with pre-built `.venv`)
- `IVY_LSP_RFC_OFFLINE=1` — disable remote RFC fetching (use local cache only)
- `IVY_LSP_RFC_CACHE_DIR=/path` — override RFC disk cache location (default: `{workspace}/.ivy-cache/rfc/`)
- `IVY_LSP_RFC_LOCAL_DIR=/path` — directory of local RFC text files (checked before remote fetch)

## LSP Indexing Awareness

When `<new-diagnostics>` contains `[ivy-lsp] indexing in progress`, the LSP is still building its workspace index:

1. **STOP** — do NOT call MCP tools (ivy_verify, ivy_coverage, ivy_diagnostics, etc.) until indexing completes
2. **Wait 10-15 seconds**, then call `ivy_status(mode="health")` to confirm readiness
3. **Indexing is complete** when the diagnostic disappears or `ivy_status(mode="health")` shows the server ready
4. The diagnostic is transient (typically 5-30 seconds after server startup)
