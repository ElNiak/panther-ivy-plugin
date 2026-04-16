# Timing and Concurrency Reference

Source of truth: `_TOOL_METADATA` and `_TOOL_TIMEOUTS` in
`ivy_lsp/mcp/tools/__init__.py`. Concurrency defaults in
`ivy_lsp/infra/config.py`.

---

## Section 1: Performance Tiers

Tier is the `tier` field in `_TOOL_METADATA`. Use it to decide whether a tool
is safe to call inline or should be deferred to a background/end-of-iteration
step.

| Tier | Typical Range | Tools |
|------|--------------|-------|
| **instant** | < 1 s | `ivy_capabilities`, `ivy_health_check`, `ivy_workspace`, `ivy_workflow_state` |
| **fast** | 1 – 30 s | `ivy_model_info`, `ivy_diagnostics`, `ivy_manifest`, `ivy_visualize`, `ivy_model_summary`, `ivy_patterns`, `ivy_pattern_scaffold`, `ivy_scope`, `ivy_find_variants`, `ivy_serdes_correlation`, `ivy_rfc` |
| **slow** | 30 s – 2 min | `ivy_include_graph`, `ivy_coverage`, `ivy_extract_requirements`, `ivy_quality`, `ivy_verification_dashboard`, `ivy_change_impact` |
| **blocking** | 2 – 10 min | `ivy_verify`, `ivy_compile`, `ivy_index`, `ivy_iut_test` |

**Notes**

- `ivy_diagnostics` is fast only when the semantic model is warm; it falls
  back to structural analysis immediately without the model.
- `ivy_coverage` is slow on first call, fast on subsequent calls once
  `ivy_verify` has warmed the model.
- `ivy_rfc` is fast when the RFC is cached locally; a cold fetch may add a few seconds.

---

## Section 2: Timeout Table

All timeouts are in seconds. The `safe_tool` decorator enforces them via
`asyncio.wait_for`.

**Override resolution order:**
1. Per-tool env var `IVY_LSP_TOOL_TIMEOUT_<TOOL_NAME_UPPER>` (unscaled, explicit value wins).
2. Base timeout from `_TOOL_TIMEOUTS` × `IVY_LSP_TOOL_TIMEOUT_SCALE` (default scale = 1.0).

**Global scale:** `IVY_LSP_TOOL_TIMEOUT_SCALE` multiplies the base timeout for
every tool that does not have a per-tool env var override. Minimum effective
timeout is always 1 s.

**Semaphore wait:** the `safe_tool` decorator times out waiting for the
concurrency slot at `timeout × 0.5`. If all slots are busy longer than that,
the call returns immediately with a queue-timeout error rather than waiting
forever.

| Tool | Base Timeout (s) | Per-Tool Override Env Var |
|------|-----------------|--------------------------|
| `ivy_verify` | 600 | `IVY_LSP_TOOL_TIMEOUT_IVY_VERIFY` |
| `ivy_compile` | 360 | `IVY_LSP_TOOL_TIMEOUT_IVY_COMPILE` |
| `ivy_index` | 300 | `IVY_LSP_TOOL_TIMEOUT_IVY_INDEX` |
| `ivy_iut_test` | 180 | `IVY_LSP_TOOL_TIMEOUT_IVY_IUT_TEST` |
| `ivy_diagnostics` | 120 | `IVY_LSP_TOOL_TIMEOUT_IVY_DIAGNOSTICS` |
| `ivy_coverage` | 120 | `IVY_LSP_TOOL_TIMEOUT_IVY_COVERAGE` |
| `ivy_change_impact` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_CHANGE_IMPACT` |
| `ivy_model_info` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_MODEL_INFO` |
| `ivy_include_graph` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_INCLUDE_GRAPH` |
| `ivy_manifest` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_MANIFEST` |
| `ivy_visualize` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_VISUALIZE` |
| `ivy_model_summary` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_MODEL_SUMMARY` |
| `ivy_patterns` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_PATTERNS` |
| `ivy_quality` | 60 | `IVY_LSP_TOOL_TIMEOUT_IVY_QUALITY` |
| `ivy_verification_dashboard` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_VERIFICATION_DASHBOARD` |
| `ivy_extract_requirements` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_EXTRACT_REQUIREMENTS` |
| `ivy_pattern_scaffold` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_PATTERN_SCAFFOLD` |
| `ivy_scope` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_SCOPE` |
| `ivy_find_variants` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_FIND_VARIANTS` |
| `ivy_serdes_correlation` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_SERDES_CORRELATION` |
| `ivy_rfc` | 30 | `IVY_LSP_TOOL_TIMEOUT_IVY_RFC` |
| `ivy_capabilities` | 10 | `IVY_LSP_TOOL_TIMEOUT_IVY_CAPABILITIES` |
| `ivy_health_check` | 10 | `IVY_LSP_TOOL_TIMEOUT_IVY_HEALTH_CHECK` |
| `ivy_workspace` | 10 | `IVY_LSP_TOOL_TIMEOUT_IVY_WORKSPACE` |
| `ivy_workflow_state` | 10 | `IVY_LSP_TOOL_TIMEOUT_IVY_WORKFLOW_STATE` |

Tools not listed in `_TOOL_TIMEOUTS` fall back to the module default of 60 s.

---

## Section 3: Concurrency Model

### Global tool semaphore

`_tool_semaphore` is a lazily-initialised `asyncio.Semaphore` created on the
first tool call. Its limit is `max_concurrent_tools` (default **4**, env var
`IVY_LSP_MAX_CONCURRENT_TOOLS`, minimum 1). The semaphore is module-level and
shared across all tool handlers in the same MCP server process.

Every tool call wrapped by `@safe_tool` must acquire this semaphore before
executing. If the semaphore is not available within `timeout × 0.5` seconds,
the call returns a queue-timeout error immediately.

### Compilation semaphore

Compilation workers are separate from the tool semaphore. The number of
concurrent compile jobs is `compile_workers` (default **2**, env var
`IVY_LSP_COMPILE_WORKERS`, minimum 1). This controls how many `ivyc`
processes can run in parallel during bulk analysis and `ivy_compile` calls.

The tool semaphore and compilation semaphore are independent. A single
`ivy_compile` call holds one tool-semaphore slot while also consuming one
compile-worker slot internally.

### Model-dependency wait behavior

Tools with `needs_model: True` in `_TOOL_METADATA` check semantic model
readiness before acquiring the semaphore. If the model is still in `pending`
or `building` state, the tool returns immediately with:

```json
{
  "success": false,
  "message": "Model is still building (~30s remaining). Use ivy_diagnostics(mode='structural') for immediate results, or retry this tool in 30 seconds.",
  "retry_after_seconds": 30
}
```

Model-dependent tools: `ivy_diagnostics`, `ivy_coverage`, `ivy_visualize`,
`ivy_model_summary`, `ivy_scope`, `ivy_find_variants`, `ivy_serdes_correlation`,
`ivy_change_impact`, `ivy_quality`.

### Local-only tools

Tools with `local_only: True` skip sidecar delegation and execute in the MCP
server process directly. These are always instant or fast:
`ivy_capabilities`, `ivy_health_check`, `ivy_workspace`, `ivy_workflow_state`,
`ivy_rfc`.

### User-supplied timeout extension

If a caller passes an explicit `timeout` parameter, `safe_tool` uses
`max(base_timeout, user_timeout + 30)` as the effective deadline. This allows
callers to extend blocking operations without bypassing the per-tool base.

---

## Section 4: Sequencing Rules

1. **Prefer structural diagnostics during iteration.** `ivy_diagnostics` with
   `mode='structural'` returns immediately without the semantic model. Reserve
   `ivy_verify` for end-of-iteration or when a full counterexample is needed.

2. **Never put blocking tools in retry loops.** `ivy_verify`, `ivy_compile`,
   `ivy_index`, and `ivy_iut_test` each hold a concurrency slot for 2–10
   minutes. Retrying them in a tight loop starves all other tools and triggers
   queue-timeout errors on subsequent calls.

3. **Model is warm after `ivy_verify`.** Once `ivy_verify` completes
   successfully, `ivy_coverage`, `ivy_model_summary`, and `ivy_visualize` will
   complete in their fast range (seconds) rather than their slow range (30+ s)
   because the semantic model is already loaded.

4. **Do not dispatch 4 blocking tools in parallel.** The global semaphore limit
   is 4. Dispatching 4 blocking tools simultaneously occupies every slot for
   minutes, making all instant and fast tools queue-timeout for the duration.
   Keep at most 1–2 blocking tools in flight at a time to leave capacity for
   diagnostic and workspace tools.

5. **RFC tools are instant when cached.** `ivy_rfc` is `local_only` and skips the sidecar. When the RFC is
   cached (TTL 3600 s, env `IVY_LSP_RFC_CACHE_TTL`), they return in under 1 s.
   A cold fetch adds a network round-trip; set `IVY_LSP_RFC_OFFLINE=1` to
   disable network fetches and rely on the local cache only.
