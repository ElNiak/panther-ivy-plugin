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

## Directory Structure

```
protocol-testing/{prot}/
├── {prot}_stack/           # Core protocol model (layers 1-9)
├── {prot}_entities/        # Entity definitions + behavior (layers 10-12)
├── {prot}_shims/           # Implementation bridge (layer 12)
├── {prot}_utils/           # Serialization + utilities (layers 13-14)
└── {prot}_tests/
    ├── server_tests/       # Ivy=client, tests server IUT
    ├── client_tests/       # Ivy=server, tests client IUT
    └── mim_tests/          # Man-in-the-middle tests
```

**Naming**: `{prot}_{layer}.ivy` for stack layers, `ivy_{prot}_{role}.ivy` for entities, `{prot}_{role}_test_*.ivy` for tests.

**Reference**: `protocol-testing/quic/` (complete, 200+ files). **Template**: `protocol-testing/new_prot/` (scaffold).

## Debugging & Troubleshooting

**Health check**: Run the `triage` workflow or call `ivy_health_check` to verify LSP + MCP are working correctly.

**Log files**:
- `/tmp/ivy-lsp-latest.log` — symlink to whichever server started last (backward compat)
- `/tmp/ivy-lsp-lsp-latest.log` — LSP server log (indexing, hover, definitions)
- `/tmp/ivy-mcp-latest.log` — MCP server log (tool calls, model building)
- Per-instance files: `ivy-lsp-<timestamp>-<pid>.log`

**Common failures**:
- LSP not starting: check if `uvx` is on PATH, check `/tmp/ivy-lsp-lsp-latest.log` for startup errors
- Empty LSP results: workspace indexing may not be complete — check LSP log for "Indexed N files"
- Z3 import error (ARM/Apple Silicon): use `development-scp-refactor` branch for stability
- MCP server unresponsive: run `ivy_capabilities` to test connectivity, check `/tmp/ivy-mcp-latest.log`

**Debug environment variables**:
- `IVY_LSP_LOG_LEVEL=DEBUG` — verbose logging
- `IVY_LSP_FORCE_REINSTALL=1` — force `uvx` to reinstall the package (not set by default; use when modifying local ivy-lsp source)
- `IVY_LSP_DEV_ROOT=/path/to/local/ivy-lsp` — use local development copy
- `PANTHER_IVY_ENABLE_SERENA=1` — enable the Serena MCP server (disabled by default; requires panther-serena submodule with pre-built `.venv`)

**Restart**: Kill the `ivy_lsp` process — Claude Code automatically restarts it on the next LSP or MCP call.

### LSP Indexing Awareness

When `<new-diagnostics>` contains `[ivy-lsp] indexing in progress`, the LSP is still building its workspace index:

1. **STOP** — do NOT call MCP tools (ivy_verify, ivy_coverage, ivy_diagnostics, etc.) until indexing completes
2. **Wait 10-15 seconds**, then call `ivy_health_check` to confirm readiness
3. **Indexing is complete** when the diagnostic disappears or `ivy_health_check` shows the server ready
4. The diagnostic is transient (typically 5-30 seconds after server startup)
