---
name: nct-validate
description: Comprehensive correctness validation of Ivy LSP, MCP tools, plugin hooks, agents, and surface coverage against the real QUIC workspace (~55 checks across 7 phases) with error injection, agent validation, and self-review
arguments:
  - name: phase
    description: "Comma-separated phases to run: preflight, mcp, fixtures, lsp, hooks, agents, surface, selfreview. Default: all"
    required: false
  - name: check
    description: "Comma-separated check IDs to run: P1, M5, L3, H2, FX1, A1, S1, SR1. Default: all in selected phases"
    required: false
  - name: error-injection
    description: "Enable mutation tests (M13-M15). Default: true when mcp phase runs"
    required: false
---

Run a comprehensive correctness validation of the Ivy LSP, MCP tools, plugin hooks, agents, and surface coverage against the real QUIC workspace. Unlike `/nct-health` (which checks connectivity), this command checks **correctness** — verifying that tools return expected values against known ground truth, injecting errors to test negative paths, validating agents dispatch correctly, and performing self-review.

## Instructions

### Argument Parsing

Parse optional arguments from the user's invocation:

1. **`phase`**: If provided, split by comma and map to phase numbers:
   - `preflight` → Phase 0
   - `mcp` → Phase 1 (includes M13-M15 error injection)
   - `fixtures` → Phase 1B
   - `lsp` → Phase 2
   - `hooks` → Phase 3
   - `agents` → Phase 4
   - `surface` → Phase 5
   - `selfreview` → Phase 6
   - If omitted, run **all** phases.

2. **`check`**: If provided, split by comma. Only run checks whose ID matches. Phase 0 still runs as gate.

3. **`error-injection`**: If `false`, skip M13–M15. Default: `true` when mcp phase runs.

**Phase dependencies**:
- Phase 0 (pre-flight) **always runs** when any downstream phase is requested.
- Phase 6 (self-review) **always runs last** (unless explicitly excluded via `phase` argument).

### Ground Truth Loading

1. Attempt to read `tests/ground-truth/quic-workspace.yaml` relative to the plugin root (`${CLAUDE_PLUGIN_ROOT}`). Use the `Read` tool on the absolute path.
2. If found, parse the YAML and use its values as ground truth throughout.
3. If not found, use the hardcoded fallback values documented inline with each check below.
4. Record which source was used in the report header.

### Pre-Mutation Safety Check (before Phase 1)

If Phase 1 will run with error injection enabled:
1. Read line 1 of the mutation target file (`quic/quic_stack/quic_types.ivy`, resolved to absolute path).
2. Verify it matches `#lang ivy1.7`.
3. If it does NOT match: a previous crashed run may have left dirty state. Read the full file content, report a warning, and attempt to verify the file is syntactically intact by running `ivy_lint`. If lint shows errors that match known mutations (missing header, unmatched brace, nonexistent include), warn the user and **skip error injection** (mark M13-M15 as SKIPPED with reason "dirty state detected").

### General Rules

- For each check: call the specified tool with exact parameters, capture **full raw output** (do not truncate), compare against expected values, record PASS/FAIL/SKIPPED with assessment reasoning.
- **Never abort early.** If a check fails, record FAIL and continue. If an entire subsystem is unavailable, mark its checks as SKIPPED and continue.
- Track all results for the Phase 6 self-review meta-analysis.

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

## Phase 1: MCP Tool Validation (15 checks)

Skip this entire phase if P2 failed.

### M1: Lint clean file (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Expected**: `diagnostic_count: 0` (clean file). Ground truth: `mcp_tools.quic_types_lint_diagnostics` (fallback: 0).
- If diagnostic_count matches: **PASS**.
- Otherwise: **FAIL** — report diagnostics.

### M2: Lint clean file (quic_frame)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_frame.ivy`

- **Expected**: `diagnostic_count: 0` (clean file). Ground truth: `mcp_tools.quic_frame_lint_diagnostics` (fallback: 0).
- If diagnostic_count matches: **PASS**.
- Otherwise: **FAIL** — report diagnostics.

### M3: Include graph (focused — quic_connection)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with:
- `relative_path`: `quic/quic_stack/quic_connection.ivy`

- **Expected**: Include count matches ground truth `mcp_tools.quic_connection_include_count` (fallback: 11). Modules match `mcp_tools.quic_connection_include_modules` (fallback: `quic_types`, `quic_transport_error_code`, `quic_time`, `quic_application`, `quic_security`, `quic_frame`, `quic_packet`, `quic_packet_retry`, `quic_packet_vn`, `quic_packet_0rtt`, `quic_packet_coal_0rtt`). All `resolved_path` values should be non-null.
- If include count matches and all modules present with resolved paths: **PASS**.
- Otherwise: **FAIL** — report actual count and any unresolved modules.

### M4: Include graph (full workspace)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with no `relative_path` argument (or empty).

- **Expected**: `total_files` matches ground truth `mcp_tools.workspace_total_files` (fallback: 680) within `mcp_tools.workspace_total_files_tolerance` (fallback: ±5).
- If total_files is within tolerance: **PASS** (report "approx" if not exact).
- Otherwise: **FAIL** — report actual count.

### M5: Verify known error (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Expected**: `success: false`; error output contains ground truth `mcp_tools.quic_types_verify_error_symbol` (fallback: `zero_rtt_allowed`).
- If success is false and expected symbol appears in error output: **PASS** — the tool correctly detects the known error.
- If success is true: **FAIL** — "Expected verification failure but got success."
- If success is false but expected symbol not in output: **FAIL** — "Different error than expected."

### M6: Symbol query (cid)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `cid`
- `protocol`: `quic`

- **Expected**: `found: true`; file path contains ground truth `mcp_tools.cid_symbol_file` (fallback: `quic_types.ivy`); line in ground truth `mcp_tools.cid_symbol_line_range` (fallback: [29, 30]).
- If found and file matches and line in range: **PASS**.
- Otherwise: **FAIL** — report actual values.

### M7: Symbol query (quic_packet_type)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `quic_packet_type`
- `protocol`: `quic`

- **Expected**: `found: true`; file path contains `quic_types.ivy`; kind matches ground truth `mcp_tools.quic_packet_type_kind` (fallback: `object`).
- If found and file matches and kind matches: **PASS**.
- Otherwise: **FAIL** — report actual values.

### M8: Coverage stats (requirements)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `stats`
- `relative_path`: `quic/`

- **Expected**: Ground truth values — `mcp_tools.coverage_total` (fallback: 97), `mcp_tools.coverage_must` (fallback: 42), `mcp_tools.coverage_must_not` (fallback: 12), `mcp_tools.coverage_should` (fallback: 16), `mcp_tools.coverage_should_not` (fallback: 3), `mcp_tools.coverage_may` (fallback: 24).
- If total matches and all level counts match: **PASS**.
- If total matches but level counts differ: **PASS (partial)** — report differences.
- Otherwise: **FAIL** — report actual values.

### M9: Coverage gaps

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `gaps`
- `protocol`: `quic`

- **Expected**: Returns a list of uncovered requirements. The uncovered count should be consistent with the stats from M8 (i.e., total minus covered equals uncovered count here).
- If uncovered count is consistent with M8 stats: **PASS**.
- Otherwise: **FAIL** — report discrepancy.

### M10: Quality gate

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_quality` with:
- `mode`: `gate`
- `protocol`: `quic`
- `gate_level`: `standard`

- **Expected**: `minimum_files` check passed (gate reports files in ground truth `mcp_tools.quality_gate_file_range` (fallback: 200-210)); `monitors_exist` check passed.
- If both checks pass: **PASS**.
- Otherwise: **FAIL** — report which checks failed.

### M11: Scaffold check

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_patterns` with:
- `mode`: `check`
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

### M13: Error Injection — ivy_lint (missing #lang header)

**Skip if `error-injection=false` or pre-mutation safety check failed.**

This check uses the backup-restore mutation pattern:

1. **Read**: Read the full content of `quic/quic_stack/quic_types.ivy` into memory (this is the backup).
2. **Pre-mutation baseline**: Run `ivy_lint` on the file. Confirm `diagnostic_count: 0`. Record this as pre-mutation output.
3. **Mutate**: Use the `Edit` tool to remove the `#lang ivy1.7` header (line 1) — replace `#lang ivy1.7` with an empty string.
4. **Test**: Run `ivy_lint` on the mutated file. **Expected**: `diagnostic_count > 0`, diagnostic message mentions "header" or "lang" or similar.
5. **Restore**: Use the `Write` tool to write the original content back (the backup from step 1).
6. **Verify recovery**: Run `ivy_lint` again. Confirm `diagnostic_count: 0`.

- **Inline self-review**: Did the error message clearly indicate what was wrong? Was it actionable?
- If mutation caused diagnostics AND recovery restored clean state: **PASS**.
- If mutation did NOT cause diagnostics: **FAIL** — "Lint did not detect missing #lang header."
- If recovery failed (still shows diagnostics): **FAIL** — "File restoration failed after mutation."

### M14: Error Injection — ivy_lint (unmatched brace)

**Skip if `error-injection=false` or pre-mutation safety check failed.**

1. **Read**: Read the full content of `quic/quic_stack/quic_types.ivy` into memory (backup).
2. **Mutate**: Use the `Edit` tool to append `{` at the very end of the file content — edit the last line to add `{` after it.
3. **Test**: Run `ivy_lint`. **Expected**: `diagnostic_count > 0`, message mentions "brace" or "unmatched" or "syntax".
4. **Restore**: Use the `Write` tool to write the original content back.
5. **Verify recovery**: Run `ivy_lint`. Confirm `diagnostic_count: 0`.

- If mutation caused diagnostics AND recovery restored clean state: **PASS**.
- If mutation did NOT cause diagnostics: **FAIL** — "Lint did not detect unmatched brace."
- If recovery failed: **FAIL** — "File restoration failed after mutation."

### M15: Error Injection — ivy_lint (nonexistent include)

**Skip if `error-injection=false` or pre-mutation safety check failed.**

1. **Read**: Read the full content of `quic/quic_stack/quic_types.ivy` into memory (backup).
2. **Mutate**: Use the `Edit` tool to insert `include nonexistent_module_xyzzy` as a new line after line 1 (`#lang ivy1.7`).
3. **Test**: Run `ivy_lint`. **Expected**: `diagnostic_count > 0`, message mentions "unresolved" or "include" or "not found".
4. **Restore**: Use the `Write` tool to write the original content back.
5. **Verify recovery**: Run `ivy_lint`. Confirm `diagnostic_count: 0`.

- If mutation caused diagnostics AND recovery restored clean state: **PASS**.
- If mutation did NOT cause diagnostics: **FAIL** — "Lint did not detect nonexistent include."
- If recovery failed: **FAIL** — "File restoration failed after mutation."

---

## Phase 1B: Fixture-Based Negative Testing (6 checks)

No file mutations — uses edge-case inputs on existing data. Skip if P2 failed.

### FX1: Symbol query — nonexistent symbol

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `nonexistent_xyzzy_42`

- **Expected**: `found: false` or empty result.
- **Inline self-review**: Verify the response is valid JSON, has a `found` key, and no stack traces.
- If found is false or symbol not found: **PASS** — graceful handling.
- If found is true: **FAIL** — "Found a nonexistent symbol."
- If error/stack trace: **FAIL** — "Ungraceful error on nonexistent symbol."

### FX2: Coverage stats — nonexistent protocol directory

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `stats`
- `relative_path`: `new_prot/`

- **Expected**: `total: 0` requirements (empty/scaffold directory).
- If total is 0 or graceful empty result: **PASS**.
- If error/stack trace: **FAIL** — "Ungraceful error on empty directory."

### FX3: Include graph — standalone file

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with:
- `relative_path`: `quic/quic_stack/quic_h3_error_code.ivy`

- **Expected**: Empty or minimal includes list (standalone file with few/no includes).
- If includes list is empty or very small (≤2): **PASS** — correctly reports standalone file.
- If large includes list returned: **FAIL** — "Unexpected includes for standalone file."

### FX4: Model summary — non-test file

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_summary` with:
- `test_file`: `quic/quic_stack/quic_transport_error_code.ivy`

- **Expected**: Graceful result (may be empty or partial — non-test file has no test actions).
- **Inline self-review**: Response should not contain stack traces or crash errors.
- If graceful result returned (even empty): **PASS**.
- If error/crash: **FAIL** — "Ungraceful error on non-test file."

### FX5: Impact analysis — known type

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `impact`
- `symbol_name`: `quic_packet_type`

- **Expected**: Non-empty impact graph (this type is widely used).
- If impact results are non-empty: **PASS** — report count.
- If empty: **FAIL** — "No impact found for widely-used type."

### FX6: Coverage gaps — nonexistent protocol

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `gaps`
- `protocol`: `new_prot`

- **Expected**: Empty gaps list or graceful "no requirements" response.
- If empty/graceful result: **PASS**.
- If error/stack trace: **FAIL** — "Ungraceful error on nonexistent protocol."

---

## Phase 2: LSP Validation (6 checks)

Skip this entire phase if P1 or P3 failed. Resolve all file paths relative to the detected Ivy workspace (the `protocol-testing/` directory).

### L1: Document symbols (quic_types)

Use the `LSP` tool to request `documentSymbol` on `quic/quic_stack/quic_types.ivy`.

- **Expected**: Symbols include ground truth `lsp.quic_types_symbols` (fallback: `cid`, `quic_packet_type`, `role`, `bit`).
- **Inline self-review**: Verify response is a list, each entry has `name` and `range` fields, line numbers are non-negative.
- If all expected symbol names found: **PASS** — report full symbol list.
- If some missing: **FAIL** — report which are missing.

### L2: Hover on type (cid)

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line matching ground truth `lsp.cid_hover_line` (fallback: 30), character matching `lsp.cid_hover_char` (fallback: 6).

- **Expected**: Returns hover info about the `cid` type.
- **Inline self-review**: Verify response has `contents` field, file path resolves to an existing file.
- If hover content mentions `cid`: **PASS** — report hover content.
- If empty or error: **FAIL**.

### L3: Go-to-definition (include quic_stream)

Use the `LSP` tool to request `goToDefinition` on `quic/quic_stack/quic_application.ivy` at line 4, character 9 (on the `quic_stream` part of `include quic_stream`).

- **Expected**: Resolves to a file path ending in `quic_stream.ivy`.
- **Inline self-review**: Verify result has `uri` and `range` fields, target file exists on disk.
- If definition target contains `quic_stream.ivy`: **PASS** — report target location.
- If no result or wrong file: **FAIL**.

### L4: Find references (cid)

Use the `LSP` tool to request `findReferences` on `quic/quic_stack/quic_types.ivy` at line matching ground truth `lsp.cid_hover_line` (fallback: 30), character matching `lsp.cid_hover_char` (fallback: 6).

- **Expected**: Returns multiple reference locations for `cid` across the workspace (more than 1 file).
- **Inline self-review**: Verify each reference has `uri` and `range`, line numbers are non-negative, file paths resolve.
- If multiple references returned: **PASS** — report count and sample files.
- If zero or one reference: **FAIL**.

### L5: Hover on action (app_server_open_event)

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_application.ivy` at line 32, character 10.

- **Expected**: Returns info about the `app_server_open_event` action with parameters.
- **Inline self-review**: Verify response has `contents` field, content is non-empty string.
- If hover content mentions `app_server_open_event` or action parameters: **PASS** — report hover content.
- If empty or error: **FAIL**.

### L6: Workspace symbol search (cid)

Use the `LSP` tool to request `workspaceSymbol` with query `cid`.

- **Expected**: Returns at least one result for `cid` with a location in `quic_types.ivy`.
- **Inline self-review**: Verify results are a list, each has `name` and `location` fields.
- If result found with correct location: **PASS** — report results.
- If empty: **FAIL**.

---

## Phase 3: Plugin Hook Validation (12 checks)

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

### H3: PreToolUse hook registered (lint-before-verify)

Verify that `hooks.json` contains a `PreToolUse` hook with matcher `"ivy_verify"` and command containing `lint-before-verify.sh`.

- If found: **PASS**.
- If not found: **FAIL** — "lint-before-verify hook not registered."

### H4: PreToolUse hook registered (observability — global)

Verify that `hooks.json` contains a `PreToolUse` hook with empty matcher `""` and command containing `obs_pre_tool_use.py`.

- If found: **PASS**.
- If not found: **FAIL** — "PreToolUse observability hook not registered."

### H5: PostToolUse hook registered (post-write-ivy-lint)

Verify that `hooks.json` contains a `PostToolUse` hook with matcher `"Write|Edit"` and command containing `post-write-ivy-lint.sh`.

- If found: **PASS**.
- If not found: **FAIL** — "post-write-ivy-lint hook not registered."

### H6: PostToolUse hook registered (observability — global)

Verify that `hooks.json` contains a `PostToolUse` hook with empty matcher `""` and command containing `obs_post_tool_use.py`.

- If found: **PASS**.
- If not found: **FAIL** — "PostToolUse observability hook not registered."

### H7: PostToolUseFailure hook registered

Verify that `hooks.json` contains a `PostToolUseFailure` section with command containing `obs_post_tool_use_failure.py`.

- If found: **PASS**.
- If not found: **FAIL** — "PostToolUseFailure hook not registered."

### H8: SessionEnd hook registered

Verify that `hooks.json` contains a `SessionEnd` section with command containing `obs_session_end.py`.

- If found: **PASS**.
- If not found: **FAIL** — "SessionEnd hook not registered."

### H9: Stop hook registered (stop-session-summary)

Verify that `hooks.json` contains a `Stop` section with command containing `stop-session-summary.sh`.

- If found: **PASS**.
- If not found: **FAIL** — "stop-session-summary hook not registered."

### H10: SubagentStart + SubagentStop hooks registered

Verify that `hooks.json` contains both:
- A `SubagentStart` section with command containing `obs_subagent_start.py`
- A `SubagentStop` section with command containing `obs_subagent_stop.py`

- If both found: **PASS**.
- If either missing: **FAIL** — report which is missing.

### H11: Remaining observability hooks registered (PreCompact, UserPromptSubmit, Notification, PermissionRequest)

Verify that `hooks.json` contains all four:
- `PreCompact` with `obs_pre_compact.py`
- `UserPromptSubmit` with `obs_user_prompt_submit.py`
- `Notification` with `obs_notification.py`
- `PermissionRequest` with `obs_permission_request.py`

- If all four found: **PASS**.
- If any missing: **FAIL** — report which are missing.

### H12: All hook scripts exist and are readable

For every script referenced in `hooks.json`, use the `Read` tool to read the first line of each script file (resolved relative to plugin root). Verify each has a shebang (`#!/`) or Python import as first line.

Scripts to check (from `hooks/scripts/`):
- `block-direct-ivy.sh`
- `lint-before-verify.sh`
- `post-write-ivy-lint.sh`
- `detect-ivy-workspace.sh`
- `stop-session-summary.sh`
- `observability/obs_pre_tool_use.py`
- `observability/obs_post_tool_use.py`
- `observability/obs_post_tool_use_failure.py`
- `observability/obs_session_start.py`
- `observability/obs_session_end.py`
- `observability/obs_stop.py`
- `observability/obs_subagent_start.py`
- `observability/obs_subagent_stop.py`
- `observability/obs_pre_compact.py`
- `observability/obs_user_prompt_submit.py`
- `observability/obs_notification.py`
- `observability/obs_permission_request.py`

- If all scripts exist and are readable: **PASS** — report count.
- If any missing: **FAIL** — report which scripts are missing.

---

## Phase 4: Agent Validation (8 checks)

Dispatch each agent with a representative task. Verify: non-empty response (>50 chars), no stack traces, output addresses the task (keyword matching with ≥2 expected keywords).

Use the `Agent` tool with the appropriate `subagent_type`. Batch agents in parallel where possible.

**Batch 1** (dispatch in parallel): A1, A3, A6, A7.
**Batch 2** (dispatch in parallel): A2, A4, A5, A8.

Timeout: 120s per agent. Mark SKIPPED on timeout or if agent dispatch fails.

### A1: spec-analyst (exploration)

Dispatch `panther-ivy-plugin:spec-analyst` with prompt:
> "Explain the structure of `quic/quic_stack/quic_types.ivy`. List the main types defined in this file."

- **Expected keywords** (≥2 must appear in response): `cid`, `quic_packet_type`, `type`, `include`
- **Inline self-review**: Response >50 chars, no stack traces, ≥2 keywords matched.
- If response is valid and keywords match: **PASS** — report response length and matched keywords.
- Otherwise: **FAIL** — report what was missing.

### A2: spec-analyst (verification)

Dispatch `panther-ivy-plugin:spec-analyst` with prompt:
> "Run formal verification on `quic/quic_stack/quic_types.ivy` and present the results."

- **Expected keywords** (≥2): `ivy_verify` or `verify`, `PASS` or `FAIL` or `error`, `verification` or `check`
- If valid: **PASS**. Otherwise: **FAIL**.

### A3: methodology-guide (NCT)

Dispatch `panther-ivy-plugin:methodology-guide` with prompt:
> "I want to add a monitor for RFC 9000 section 4.1. Which NCT step am I at and what should I do next?"

- **Expected keywords** (≥2): `NCT`, `step` or `workflow`, `before` or `after` or `monitor`
- If valid: **PASS**. Otherwise: **FAIL**.

### A4: methodology-guide (NACT)

Dispatch `panther-ivy-plugin:methodology-guide` with prompt:
> "How would I model a man-in-the-middle attack on the QUIC initial handshake using NACT?"

- **Expected keywords** (≥2): `NACT` or `APT`, `infiltration` or `attack`, `MIM` or `man-in-the-middle` or `entity`
- If valid: **PASS**. Otherwise: **FAIL**.

### A5: methodology-guide (NSCT)

Dispatch `panther-ivy-plugin:methodology-guide` with prompt:
> "How do I configure Shadow NS for QUIC testing with 50ms latency?"

- **Expected keywords** (≥2): `Shadow` or `shadow_ns` or `NSCT`, `simulation` or `latency` or `topology`
- If valid: **PASS**. Otherwise: **FAIL**.

### A6: model-reviewer (review)

Dispatch `panther-ivy-plugin:model-reviewer` with prompt:
> "Review `quic/quic_stack/quic_types.ivy` for correctness and quality issues."

- **Expected keywords** (≥2): `ERROR` or `WARNING` or `INFO` or `issue`, `review` or `quality` or `suggestion`
- If valid: **PASS**. Otherwise: **FAIL**.

### A7: traceability-agent (extraction)

Dispatch `panther-ivy-plugin:traceability-agent` with prompt:
> "What is the current RFC 9000 requirement coverage for the QUIC protocol?"

- **Expected keywords** (≥2): `coverage`, `MUST` or `SHOULD` or `MAY`, `requirements` or `requirement`
- If valid: **PASS**. Otherwise: **FAIL**.

### A8: traceability-agent (gap review)

Dispatch `panther-ivy-plugin:traceability-agent` with prompt:
> "Are there orphaned RFC tags or coverage gaps in `quic/quic_stack/quic_connection.ivy`?"

- **Expected keywords** (≥2): `tag` or `tags`, `coverage` or `gap` or `orphan`
- If valid: **PASS**. Otherwise: **FAIL**.

---

## Phase 5: Surface Coverage (4 checks)

### S1: Commands count

Use `Glob` to find `commands/*.md` relative to the plugin root (excluding `README.md`). For each file, verify YAML frontmatter contains `name` and `description` fields.

- **Expected**: Ground truth `surface.command_count` (fallback: 9) command files, each with valid frontmatter.
- If count matches and all have valid frontmatter: **PASS**.
- Otherwise: **FAIL** — report actual count and any missing frontmatter.

### S2: Skills count

Use `Glob` to find `skills/*/SKILL.md` relative to the plugin root. For each file, verify YAML frontmatter contains `name` and `description` fields.

- **Expected**: Ground truth `surface.skill_count` (fallback: 11) skill files with valid frontmatter.
- If count matches and all have valid frontmatter: **PASS**.
- Otherwise: **FAIL** — report actual count.

### S3: MCP tools count

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` and count the reported tools.

- **Expected**: ≥ ground truth `surface.min_mcp_tools` (fallback: 15) tools reported.
- If count meets minimum: **PASS** — report actual count.
- Otherwise: **FAIL** — "Too few MCP tools reported."

### S4: Observability log validation

Check for the observability log directory. Look for JSONL log files. If found, validate:
1. File is valid JSONL (each line is parseable JSON).
2. At least one `SessionStart` event is present.

- If valid JSONL with ≥1 SessionStart event: **PASS**.
- If log directory exists but no SessionStart: **PASS (partial)** — "Logs exist but no SessionStart (may be fresh session)."
- If no log directory or no files: **SKIPPED** — "No observability logs found (fresh session)."

To find logs: check for files matching `~/.claude/ivy-observability/*.jsonl` or `$TMPDIR/ivy-obs-*.jsonl`. Use Bash to list the directory.

---

## Phase 6: Self-Review (1 meta-check)

### SR1: Holistic meta-analysis

Run this after all other phases complete. Analyze the complete set of results:

1. **Completeness**: Every check produced PASS, FAIL, or SKIPPED (no undefined status). Count any missing results.

2. **Consistency**: Cross-check related results:
   - M8 total should equal sum of MUST + MUST NOT + SHOULD + SHOULD NOT + MAY
   - M9 uncovered count should be consistent with M8 coverage (total minus covered = uncovered)
   - S3 MCP tool count should be ≥ the number of distinct MCP tools actually called during validation

3. **Format**: No truncated outputs, no empty assessments in any check.

4. **Ground truth drift**: For each numeric ground truth value, calculate the deviation from the YAML (or fallback). Flag any value differing by >5% from ground truth. If >3 values have drifted, recommend updating the ground truth YAML.

5. **Actionability**: Every FAIL has a specific suggested action (not just "check logs").

6. **Meta-quality score**: Calculate as:
   ```
   score = 100 × (pass_rate × 0.6 + ground_truth_stability × 0.2 + self_review_quality × 0.2)
   ```
   Where:
   - `pass_rate` = passed / (passed + failed) — excludes SKIPPED
   - `ground_truth_stability` = 1.0 - (drifted_values / total_ground_truth_values)
   - `self_review_quality` = 1.0 if all FAILs have actions and no truncation; deduct 0.1 per issue

- If all sub-checks pass (completeness, consistency, format, actionability): **PASS** with score.
- If any issue found: **FAIL** — report each issue.

---

## Result Presentation

Present the final results in this format:

```markdown
# Ivy Integration Validation Report (v2)

**Date**: {timestamp}
**Workspace**: {detected workspace root}
**Command**: `/nct-validate {args}`
**Phases**: {list of phases that ran}
**Ground truth**: {yaml path or "hardcoded fallback"}

## Summary

| Phase | Name | Checks | Passed | Failed | Skipped |
|-------|------|--------|--------|--------|---------|
| 0 | Pre-flight | 3 | ? | ? | ? |
| 1 | MCP Tools | 15 | ? | ? | ? |
| 1B | Fixtures | 6 | ? | ? | ? |
| 2 | LSP | 6 | ? | ? | ? |
| 3 | Hooks | 12 | ? | ? | ? |
| 4 | Agents | 8 | ? | ? | ? |
| 5 | Surface | 4 | ? | ? | ? |
| 6 | Self-Review | 1 | ? | ? | ? |
| **Total** | | **~55** | **?** | **?** | **?** |

**Meta-Quality Score**: NN/100
```

### Per-check detail format

For standard checks (P, M1-M12, L, H, FX, S):
```markdown
### {ID}: {Title}
- **Tool**: {tool name and params}
- **Status**: PASS / FAIL / SKIPPED
- **Raw Output**:
{full output here}
- **Expected**: {ground truth value}
- **Inline self-review**: {validation notes}
- **Assessment**: {reasoning}
```

For error injection checks (M13-M15):
```markdown
### {ID}: Error Injection — {description}
- **Mutation**: {what was changed}
- **Pre-mutation**: {raw output, diagnostic_count=0}
- **Post-mutation**: {raw output, diagnostic_count>0}
- **Recovery**: {raw output, diagnostic_count=0}
- **Inline self-review**: Error actionable? {yes/no}. File restored? {yes/no}.
- **Status**: PASS / FAIL
```

For agent checks (A1-A8):
```markdown
### {ID}: {agent} ({facet})
- **Dispatch prompt**: {prompt}
- **Response length**: N chars
- **Keywords matched**: {list}
- **Stack traces**: none / {details}
- **Status**: PASS / FAIL / SKIPPED
```

### Ground Truth Comparison Table

```markdown
## Ground Truth Comparison

| Key | Expected | Actual | Match | Drift |
|-----|----------|--------|-------|-------|
| quic_connection include count | 11 | ? | ? | ? |
| workspace total .ivy files | 680 | ? | ? | ? |
| total requirements | 97 | ? | ? | ? |
| MUST requirements | 42 | ? | ? | ? |
| MUST NOT requirements | 12 | ? | ? | ? |
| SHOULD requirements | 16 | ? | ? | ? |
| SHOULD NOT requirements | 3 | ? | ? | ? |
| MAY requirements | 24 | ? | ? | ? |
| cid symbol line | 29-30 | ? | ? | ? |
| quic_types known error | zero_rtt_allowed | ? | ? | ? |
| quic_packet_type kind | object | ? | ? | ? |
| commands count | 9 | ? | ? | ? |
| skills count | 11 | ? | ? | ? |
| MCP tools count | ≥15 | ? | ? | ? |
| hook event types | 12 | ? | ? | ? |
```

---

## Suggested Actions

If any checks fail, add a `### Suggested Actions` section at the end:

- If P1 fails: "Start the Ivy LSP server. Check if `ivy_lsp` is installed and in PATH."
- If P2 fails: "The MCP server is not reachable. Check plugin configuration and `/tmp/ivy-lsp.log`."
- If P3 fails: "LSP is running but not responding to requests. Check workspace indexing in `/tmp/ivy-lsp.log`."
- If any M1-M12 check fails: "MCP tool returned unexpected values. Compare raw output against ground truth in `tests/ground-truth/quic-workspace.yaml`."
- If any M13-M15 check fails: "Error injection test failed. Check that `ivy_lint` properly detects the mutation type. Verify file was restored cleanly with `git diff`."
- If any FX check fails: "Fixture test failed — tool did not handle edge-case input gracefully. Check tool error handling in the MCP server."
- If any L-check fails: "LSP feature returned unexpected results. Check `/tmp/ivy-lsp.log` for errors. Line numbers may have shifted if .ivy files were edited."
- If H1 fails: "SessionStart hook did not fire. Check `hooks/hooks.json` and `hooks/scripts/detect-ivy-workspace.sh`."
- If H2-H11 fail: "Hook not registered. Check `hooks/hooks.json` for the expected event type and script path."
- If H12 fails: "Hook script(s) missing or unreadable. Verify script files exist in `hooks/scripts/`."
- If any A-check fails: "Agent did not respond as expected. Verify agent definition in `agents/` directory. Check that the agent's tools are available."
- If any S-check fails: "Surface coverage gap detected. Verify command/skill/agent files exist with proper YAML frontmatter."
- If SR1 fails: "Self-review found issues. Address the specific sub-check failures listed in the SR1 details."
- If `protocol-testing/` directory is missing: "Protocol models not found. Run `git submodule update --init` from the panther_ivy directory."
- If ground truth drift >5%: "Consider updating `tests/ground-truth/quic-workspace.yaml` with current values."

See the `tooling-reference` skill for tool architecture.
