---
name: nct-validate
description: Comprehensive correctness validation of Ivy LSP, MCP tools, and plugin hooks against the real QUIC workspace with full raw-output report
arguments: []
---

Run a comprehensive correctness validation of the Ivy LSP, MCP tools, and plugin hooks against the real QUIC workspace. Unlike `/nct-health` (which checks connectivity), this command checks **correctness** — verifying that tools return expected values against known ground truth.

## Instructions

Run all 23 checks across 4 phases. For each check:
1. Call the specified tool with exact parameters
2. Capture the **full raw output** (do not truncate)
3. Compare against the expected values
4. Record PASS, FAIL, or SKIPPED with assessment reasoning

**Never abort early.** If a check fails, record FAIL and continue. If an entire subsystem is unavailable (e.g., LSP not running), mark its checks as SKIPPED and continue.

---

## Phase 0: Pre-flight (3 checks)

### P1: LSP process alive

Run via Bash:
```
pgrep -f ivy_lsp
```

- If PIDs are returned: **PASS** — report PID(s).
- If no output or error: **FAIL** — "No ivy_lsp process found." Mark all Phase 2 (LSP) checks as SKIPPED.

### P2: MCP server health

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- **Expected**: `success: true`, with `ivy_check: true`, `ivyc: true`, `ivy_show: true` all present.
- If all three capability flags are true: **PASS**.
- If any flag is false or tool errors: **FAIL**. Mark all Phase 1 (MCP) checks as SKIPPED.

### P3: LSP responding

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line 1, character 0 (resolve to absolute path in the detected workspace).

- If any response (even empty hover): **PASS** — LSP is responding.
- If timeout or error: **FAIL**. Mark all Phase 2 (LSP) checks as SKIPPED.

---

## Phase 1: MCP Tool Validation (12 checks)

Skip this entire phase if P2 failed.

### M1: Lint clean file (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Expected**: `diagnostic_count: 0` (clean file).
- If diagnostic_count is 0: **PASS**.
- Otherwise: **FAIL** — report diagnostics.

### M2: Lint clean file (quic_frame)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_frame.ivy`

- **Expected**: `diagnostic_count: 0` (clean file).
- If diagnostic_count is 0: **PASS**.
- Otherwise: **FAIL** — report diagnostics.

### M3: Include graph (focused — quic_connection)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with:
- `relative_path`: `quic/quic_stack/quic_connection.ivy`

- **Expected**: Exactly **11 includes** with these modules: `quic_types`, `quic_transport_error_code`, `quic_time`, `quic_application`, `quic_security`, `quic_frame`, `quic_packet`, `quic_packet_retry`, `quic_packet_vn`, `quic_packet_0rtt`, `quic_packet_coal_0rtt`. All `resolved_path` values should be non-null.
- If include count is 11 and all modules present with resolved paths: **PASS**.
- Otherwise: **FAIL** — report actual count and any unresolved modules.

### M4: Include graph (full workspace)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with no `relative_path` argument (or empty).

- **Expected**: `total_files: 680`.
- If total_files is 680: **PASS**.
- If within ±5 of 680: **PASS (approx)** — report actual count.
- Otherwise: **FAIL** — report actual count.

### M5: Verify known error (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Expected**: `success: false`; error output contains the string `zero_rtt_allowed` (a known undefined symbol at line 134).
- If success is false and `zero_rtt_allowed` appears in error output: **PASS** — the tool correctly detects the known error.
- If success is true: **FAIL** — "Expected verification failure but got success."
- If success is false but `zero_rtt_allowed` not in output: **FAIL** — "Different error than expected."

### M6: Symbol query (cid)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query_symbol` with:
- `symbol_name`: `cid`
- `protocol`: `quic`

- **Expected**: `found: true`; file path contains `quic_types.ivy`; line is 29 or 30.
- If found and file matches and line in {29, 30}: **PASS**.
- Otherwise: **FAIL** — report actual values.

### M7: Symbol query (quic_packet_type)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query_symbol` with:
- `symbol_name`: `quic_packet_type`
- `protocol`: `quic`

- **Expected**: `found: true`; file path contains `quic_types.ivy`; kind is `object`.
- If found and file matches and kind is object: **PASS**.
- Otherwise: **FAIL** — report actual values.

### M8: Coverage stats (requirements)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_requirement_coverage` with:
- `relative_path`: `quic/`

- **Expected**: `total: 101` with breakdown: MUST=45, MUST NOT=12, SHOULD=17, SHOULD NOT=3, MAY=24.
- If total is 101 and all level counts match: **PASS**.
- If total matches but level counts differ: **PASS (partial)** — report differences.
- Otherwise: **FAIL** — report actual values.

### M9: Coverage gaps

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage_gaps` with:
- `protocol`: `quic`

- **Expected**: Returns a list of uncovered requirements. The uncovered count should be consistent with the stats from M8 (i.e., total minus covered equals uncovered count here).
- If uncovered count is consistent with M8 stats: **PASS**.
- Otherwise: **FAIL** — report discrepancy.

### M10: Quality gate

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_quality_gate` with:
- `protocol`: `quic`
- `gate_level`: `standard`

- **Expected**: `minimum_files` check passed (gate reports 200-210 files); `monitors_exist` check passed.
- If both checks pass: **PASS**.
- Otherwise: **FAIL** — report which checks failed.

### M11: Scaffold check

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_scaffold_check` with:
- `protocol`: `quic`

- **Expected**: `recovery` and `extensions` layers present in completeness report; `has_manifest: true`.
- If layers present and manifest exists: **PASS**.
- Otherwise: **FAIL** — report missing layers.

### M12: Model summary

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_summary` with:
- `test_file`: `quic/`

- **Expected**: Returns per-action requirement counts (non-empty result).
- If non-empty summary returned: **PASS** — report action count.
- Otherwise: **FAIL**.

---

## Phase 2: LSP Validation (6 checks)

Skip this entire phase if P1 or P3 failed. Resolve all file paths relative to the detected Ivy workspace (the `protocol-testing/` directory).

### L1: Document symbols (quic_types)

Use the `LSP` tool to request `documentSymbol` on `quic/quic_stack/quic_types.ivy`.

- **Expected**: Symbols include `cid` (around line 30), `quic_packet_type`, `role`, and `bit`.
- If all four symbol names found: **PASS** — report full symbol list.
- If some missing: **FAIL** — report which are missing.

### L2: Hover on type (cid)

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line 30, character 6.

- **Expected**: Returns hover info about the `cid` type.
- If hover content mentions `cid`: **PASS** — report hover content.
- If empty or error: **FAIL**.

### L3: Go-to-definition (include quic_stream)

Use the `LSP` tool to request `goToDefinition` on `quic/quic_stack/quic_application.ivy` at line 4, character 9 (on the `quic_stream` part of `include quic_stream`).

- **Expected**: Resolves to a file path ending in `quic_stream.ivy`.
- If definition target contains `quic_stream.ivy`: **PASS** — report target location.
- If no result or wrong file: **FAIL**.

### L4: Find references (cid)

Use the `LSP` tool to request `findReferences` on `quic/quic_stack/quic_types.ivy` at line 30, character 6.

- **Expected**: Returns multiple reference locations for `cid` across the workspace (more than 1 file).
- If multiple references returned: **PASS** — report count and sample files.
- If zero or one reference: **FAIL**.

### L5: Hover on action (app_server_open_event)

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_application.ivy` at line 32, character 10.

- **Expected**: Returns info about the `app_server_open_event` action with parameters.
- If hover content mentions `app_server_open_event` or action parameters: **PASS** — report hover content.
- If empty or error: **FAIL**.

### L6: Workspace symbol search (cid)

Use the `LSP` tool to request `workspaceSymbol` with query `cid`.

- **Expected**: Returns at least one result for `cid` with a location in `quic_types.ivy`.
- If result found with correct location: **PASS** — report results.
- If empty: **FAIL**.

---

## Phase 3: Plugin Hook Validation (2 checks)

### H1: SessionStart hook fired

Read the beginning of this session's system-reminder messages (already in your context) and look for the `[ivy-workspace] Detected PANTHER project` message.

- **Expected**: The message is present, indicating the SessionStart hook detected the workspace.
- If message found in session context: **PASS** — quote the message.
- If not found: **FAIL** — "SessionStart hook did not fire or workspace not detected."

### H2: PreToolUse hook registered (block-direct-ivy)

Use the `Read` tool to read `hooks/hooks.json` (relative to the plugin root). Verify that a `PreToolUse` hook exists with matcher `"Bash"` and command containing `block-direct-ivy.sh`.

- **Expected**: Hook entry exists with matcher "Bash" and script path `block-direct-ivy.sh`.
- If found: **PASS** — report the hook entry.
- If not found: **FAIL** — "block-direct-ivy hook not registered."

---

## Result Presentation

Present the final results in this format:

```markdown
# Ivy Integration Validation Report

**Date**: {timestamp}
**Workspace**: {detected workspace root}
**Command**: `/nct-validate`

## Summary

| Phase | Checks | Passed | Failed | Skipped |
|-------|--------|--------|--------|---------|
| Pre-flight | 3 | ? | ? | ? |
| MCP Tools | 12 | ? | ? | ? |
| LSP | 6 | ? | ? | ? |
| Hooks | 2 | ? | ? | ? |
| **Total** | **23** | **?** | **?** | **?** |

## Phase 0: Pre-flight

### P1: LSP Process Alive
- **Tool**: `Bash: pgrep -f ivy_lsp`
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: Process PIDs returned
- **Assessment**: {reasoning}

### P2: MCP Server Health
- **Tool**: `ivy_capabilities`
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: success=true, ivy_check=true, ivyc=true, ivy_show=true
- **Assessment**: {reasoning}

### P3: LSP Responding
- **Tool**: `LSP hover` on quic_types.ivy line 1, char 0
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: Any response (even empty hover)
- **Assessment**: {reasoning}

## Phase 1: MCP Tool Validation

### M1: Lint clean file (quic_types)
- **Tool**: `ivy_lint` on quic/quic_stack/quic_types.ivy
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: diagnostic_count = 0
- **Assessment**: {reasoning}

{... M2 through M12 follow same format ...}

## Phase 2: LSP Validation

### L1: Document symbols (quic_types)
- **Tool**: `LSP documentSymbol` on quic_types.ivy
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: Symbols include cid, quic_packet_type, role, bit
- **Assessment**: {reasoning}

{... L2 through L6 follow same format ...}

## Phase 3: Plugin Hook Validation

### H1: SessionStart hook fired
- **Tool**: Session context inspection
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: [ivy-workspace] message present
- **Assessment**: {reasoning}

{... H2 follows same format ...}

## Ground Truth Comparison

| Key | Expected | Actual | Match |
|-----|----------|--------|-------|
| quic_connection include count | 11 | ? | ? |
| workspace total .ivy files | 680 | ? | ? |
| total requirements | 101 | ? | ? |
| MUST requirements | 45 | ? | ? |
| MUST NOT requirements | 12 | ? | ? |
| SHOULD requirements | 17 | ? | ? |
| SHOULD NOT requirements | 3 | ? | ? |
| MAY requirements | 24 | ? | ? |
| cid symbol line | 29-30 | ? | ? |
| quic_types known error | zero_rtt_allowed | ? | ? |
| quic_packet_type kind | object | ? | ? |
| quic .ivy file count | 202 | ? | ? |
```

If any checks fail, add a `### Suggested Actions` section at the end:

- If P1 fails: "Start the Ivy LSP server. Check if `ivy_lsp` is installed and in PATH."
- If P2 fails: "The MCP server is not reachable. Check plugin configuration and `/tmp/ivy-lsp.log`."
- If P3 fails: "LSP is running but not responding to requests. Check workspace indexing in `/tmp/ivy-lsp.log`."
- If any M-check fails: "MCP tool returned unexpected values. Compare raw output against ground truth in `ivy-lsp/tests/ground_truth/quic_workspace.json`."
- If any L-check fails: "LSP feature returned unexpected results. Check `/tmp/ivy-lsp.log` for errors. Line numbers may have shifted if .ivy files were edited."
- If H1 fails: "SessionStart hook did not fire. Check `hooks/hooks.json` and `hooks/scripts/detect-ivy-workspace.sh`."
- If H2 fails: "PreToolUse hook not registered. Check `hooks/hooks.json` for the Bash matcher entry."
- If `protocol-testing/` directory is missing: "Protocol models not found. Run `git submodule update --init` from the panther_ivy directory."
