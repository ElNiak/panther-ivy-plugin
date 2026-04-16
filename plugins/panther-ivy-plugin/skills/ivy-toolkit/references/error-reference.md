# Cross-Cutting Error Reference

Errors that span multiple tools or need non-obvious recovery strategies.
Tool-specific errors are in tool-catalog.md per-tool entries.

---

## 1. Model Not Ready

**Pattern:**
```json
{
  "success": false,
  "tool": "<tool_name>",
  "message": "Model is still building (~30s remaining). Use ivy_diagnostics(mode='structural') for immediate results, or retry this tool in 30 seconds.",
  "retry_after_seconds": 30
}
```

**Tools:** ivy_diagnostics, ivy_coverage, ivy_visualize, ivy_model_summary, ivy_scope, ivy_find_variants, ivy_serdes_correlation, ivy_change_impact, ivy_quality (any tool with `needs_model: true`)

**Cause:** The semantic model (LSP index) is still building after server startup or after `ivy_index` is triggered. Tools that depend on the model (`needs_model: true`) short-circuit immediately rather than blocking.

**Recovery:**
1. Use `ivy_diagnostics(mode="structural")` for immediate syntax/include diagnostics — it does not require the semantic model.
2. Wait 30 seconds and retry the original tool.
3. If the model never becomes ready, call `ivy_health_check` to verify the indexer state and check for errors.
4. If `ivy_health_check` shows a stuck indexer, restart the MCP server.

---

## 2. Workspace Not Set

**Pattern:**
```json
{ "success": false, "message": "Unknown workspace group '<target>'. Available groups: <list>." }
```
or (when target is omitted for action='set'):
```json
{ "success": false, "message": "action='set' requires a 'target' parameter." }
```

**Tools:** ivy_workspace (action='set'), and indirectly any tool that narrows scope using `ivy_workspace` state (ivy_coverage, ivy_diagnostics, ivy_scope)

**Cause:** The requested workspace group name does not exist in the loaded workspace configuration, or no target was provided for `action='set'`.

**Recovery:**
1. Call `ivy_workspace(action="list")` to see available groups (e.g. `"quic"`, `"bgp"`).
2. Use the exact group name from that list in a subsequent `ivy_workspace(action="set", target="<group>")` call.
3. To set scope to a specific test file, pass an `.ivy` file path as `target` instead of a group name.
4. If no groups are listed at all, the workspace configuration has not been loaded — restart the MCP server with a valid workspace config file.

---

## 3. RFC Service Not Initialized

**Pattern:**
```json
{ "success": false, "message": "RFC service not initialized." }
```

**Tools:** ivy_rfc_get, ivy_rfc_search, ivy_rfc_section

**Cause:** The RFC service (`ctx.rfc_service`) was not started, which happens when the MCP server is launched without the RFC service dependency or when its initialization failed at startup.

**Recovery:**
1. Restart the MCP server; the RFC service initializes automatically at startup.
2. Check MCP server logs for RFC service initialization errors (look for `RFCService` or `rfc_service` in startup output).
3. Verify network access to `datatracker.ietf.org` is not blocked if the service requires a connectivity check at startup.

---

## 4. Network Failure (RFC Fetch)

**Pattern:**
```json
{ "success": false, "message": "Failed to fetch RFC <number>: <exception detail>" }
```
or for search:
```json
{ "success": false, "message": "Search failed: <exception detail>" }
```

**Tools:** ivy_rfc_get, ivy_rfc_search, ivy_rfc_section

**Cause:** The HTTP request to `datatracker.ietf.org` (or the IETF RFC index) failed. Common causes: network unavailable, DNS failure, IETF service temporarily down, or firewall blocking outbound HTTP.

**Recovery:**
1. Check network connectivity: `curl -I https://datatracker.ietf.org` from the same host.
2. Retry after a short delay — IETF services occasionally have brief outages.
3. If the RFC was fetched previously, the local disk cache may still have it. The fetch order is: memory cache → disk cache → network. A network failure only affects documents not yet cached locally.
4. If the environment has no outbound internet access, pre-populate the disk cache by fetching the required RFC documents from a connected machine and copying the cache directory.

---

## 5. Compilation Failure

**Pattern:**
```json
{
  "success": false,
  "diagnostics": [{ "severity": "error", "file": "...", "line": N, "message": "..." }],
  "error_summary": "...",
  "raw_output": "..."
}
```
or (compiler not available):
```json
{ "success": false, "message": "ivyc CLI not found on PATH and no Docker image configured. ..." }
```
or (Docker setup failure):
```json
{ "success": false, "message": "Docker setup failed (exit <code>)", "raw_output": "..." }
```

**Tools:** ivy_compile

**Cause:** The Ivy source file contains syntax or semantic errors that prevent compilation, the `ivyc` CLI is not available on `PATH`, or the Docker executor failed during setup.

**Recovery:**
1. If `ivyc` is missing: run `ivy_verify` first — it also checks availability via `ivy_check`. Both tools require Ivy to be installed, typically inside a Docker container built by PANTHER. Run `panther run` with a config to build the Docker environment.
2. If Docker setup failed: check the `raw_output` field for the exit code and stderr. Common causes are missing base images or Docker daemon not running.
3. If compilation failed with diagnostics: read the `diagnostics` array. Each entry has `file`, `line`, and `message`. Fix errors starting from the first (errors cascade). Use `ivy_diagnostics(mode="structural")` for a faster structural pre-check before recompiling.
4. If the result includes `"fallback": "subprocess"` with a `fallback_reason`, Docker failed and compilation fell back to native subprocess — check `fallback_reason` for the Docker error.

---

## 6. Verification Failure / Counterexample

**Pattern:**
```json
{
  "success": false,
  "diagnostics": [...],
  "counterexample_trace": "...",
  "cached": false
}
```
The `counterexample_trace` field contains a formatted event trace when `ivy_check` found a property violation. In `compact=true` mode (default), the raw `counterexample` object and `raw_output` are stripped; only `counterexample_trace` is kept.

**Tools:** ivy_verify

**Cause:** `ivy_check` found a reachable counterexample — a sequence of events that violates a `require`, `ensure`, or `invariant` property in the Ivy model. This is a specification bug, not an infrastructure failure.

**Recovery:**
1. Read `counterexample_trace` for the event sequence leading to the violation.
2. Identify the failing assertion: the last event in the trace that triggers a `require`/`ensure`/`invariant` check.
3. Use `ivy_diagnostics` to cross-check the same file for structural issues that might indicate a mis-scoped assumption.
4. To see the full counterexample object, call `ivy_verify` again with `compact=false`.
5. To see raw `ivy_check` output, call `ivy_verify` with `compact=false` and read `raw_output`.
6. If the violation is in a `require` on an exported action, the requirement is treated as an assumption about the environment — check whether the environment can actually violate it (see ivy_test_compilation rules in project memory).

---

## 7. Tool Timeout

**Pattern:**
```json
{ "success": false, "message": "Tool timed out after <N>s", "timeout": true, "tool": "<tool_name>" }
```
or (concurrency slot timeout):
```json
{ "success": false, "message": "Tool queued too long (><N>s). Other tools may be stuck.", "timeout": true, "tool": "<tool_name>" }
```

**Tools:** Any tool (enforced by the `safe_tool` decorator)

**Cause:** The tool exceeded its configured timeout (`_TOOL_TIMEOUTS` in `tools/__init__.py`) or waited too long for a concurrency semaphore slot. Blocking tools (ivy_verify: 600s, ivy_compile: 360s, ivy_index: 300s, ivy_iut_test: 180s) are most common. The concurrency slot timeout is 50% of the tool's full timeout.

**Recovery:**
1. For ivy_verify: pass a higher `timeout` parameter (e.g. `timeout=300.0`). The safe_tool decorator uses `max(base_timeout, user_timeout + 30)` to extend the outer wrapper.
2. For concurrency slot timeouts ("queued too long"): other tools may be blocking slots. Check `ivy_health_check` for in-flight tool counts. Avoid dispatching 4+ blocking tools in parallel.
3. Override timeouts via environment variables: `IVY_LSP_TOOL_TIMEOUT_<TOOL_NAME_UPPER>=<seconds>` (e.g. `IVY_LSP_TOOL_TIMEOUT_IVY_VERIFY=900`).
4. Use `IVY_LSP_TOOL_TIMEOUT_SCALE` for a global multiplier (e.g. `IVY_LSP_TOOL_TIMEOUT_SCALE=2.0` doubles all timeouts).
5. For ivy_verify on complex models: use `isolate=<name>` to verify one isolate at a time rather than the whole model.

---

## 8. MCP Server Unreachable

**Pattern:** No JSON response at all — Claude Code reports a tool call error or connection failure at the MCP transport layer, not inside tool output.

Internally logged as: `[SIDECAR-ERROR] <tool_name> call failed` (warning level in server logs).

**Tools:** Any tool (transport-level, not inside tool result)

**Cause:** The MCP server process crashed, was never started, or the SSE/streamable-HTTP connection was dropped. Common causes: stale PID files, port conflicts, OOM kill, or the server exiting during a long compilation.

**Recovery:**
1. Run `ivy_health_check` if any tool responds — if this also fails, the server is down.
2. Check for stale PID/port files: `/tmp/ivy-mcp-<ws_hash>.pid` and `/tmp/ivy-mcp-<ws_hash>.port`. Delete stale files and restart.
3. Restart the MCP server. For panther-ivy-plugin: restart via `panther run` or the Claude Code MCP server configuration.
4. Check server logs (`~/.ivy-lsp/ivy-mcp-server.log` or the path configured in the server startup) for crash tracebacks.
5. If the crash repeats on a specific tool call, the tool is triggering an unhandled exception that escapes `safe_tool`. File a bug with the tool name and input parameters.

---

## 9. Sidecar Delegation Failure

**Pattern:** The sidecar call is silently skipped and the tool falls through to local execution. No user-visible error is produced — this is a transparent fallback. Server logs show:

```
[TOOL-ROUTE] <tool_name> -> local (sidecar fallback)
[SIDECAR-ERROR] <tool_name> call failed
```
or:
```
[SIDECAR-TIMEOUT] <tool_name> timed out after <N>s
```

**Tools:** All non-`local_only` tools (ivy_verify, ivy_compile, ivy_diagnostics, ivy_coverage, ivy_include_graph, ivy_index, ivy_model_info, ivy_quality, ivy_scope, ivy_visualize, ivy_model_summary, ivy_manifest, ivy_extract_requirements, ivy_patterns, ivy_pattern_scaffold, ivy_find_variants, ivy_serdes_correlation, ivy_change_impact, ivy_iut_test)

**Cause:** The sidecar process is unreachable or returned an error. `call_sidecar_once` returns `None` on any exception (including `TimeoutError`, connection refused, or HTTP error), causing `_try_sidecar_delegation` to fall through to local execution. The tool then runs locally, which is the intended fallback. `local_only` tools (ivy_capabilities, ivy_health_check, ivy_workspace, ivy_workflow_state, ivy_rfc_get, ivy_rfc_search, ivy_rfc_section) never attempt sidecar delegation.

**Recovery:**
1. In most cases this requires no action — local fallback produces correct results.
2. If local execution is significantly slower than expected (e.g. ivy_verify taking much longer than on the sidecar), check whether the sidecar is running: look for `/tmp/ivy-mcp-<ws_hash>.port` and verify the port is alive with `curl http://127.0.0.1:<port>/health`.
3. To diagnose: enable debug logging (`IVY_LSP_DEBUG=1`) and look for `[SIDECAR-ERROR]` lines with full tracebacks.
4. If the sidecar workspace root does not match the current workspace root, the sidecar is rejected (workspace mismatch). Restart the sidecar from the correct working directory.
5. Adjust sidecar delegation timeout via `IVY_LSP_SIDECAR_DELEGATION_TIMEOUT=<seconds>` if the sidecar is slow to respond.
