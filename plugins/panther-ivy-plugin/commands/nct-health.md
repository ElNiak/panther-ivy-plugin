---
name: nct-health
description: Run a health check sequence for the Ivy LSP + MCP integration
arguments: []
---
<!-- MODE: HYBRID — multi-phase checks with agent dispatch -->

Run a comprehensive health check of the Ivy LSP and MCP integration stack, reporting PASS/FAIL for each step.

## Principles

1. **Trigger-first**: MCP and LSP tools run before infrastructure checks (PIDs/logs are stale until triggered).
2. **Content validation**: Each step cross-validates tool output against ground truth using native tools (Read/Grep/Glob). A tool returning data without errors is necessary but NOT sufficient — the data must be semantically correct.
3. **Phase review**: After each phase, a reviewer agent audits the collected results for consistency, false positives, and missed failures.

## Instructions

**Workspace Status**: Before running checks, call `ivy_workspace(action="get")` to confirm the active workspace. Report the current workspace state as a preliminary line in the results table.

Run the following 9 checks in order across 3 phases. For each check, record PASS, WARN, or FAIL with a short detail message. If a check fails, continue with the remaining checks (do not abort early) **unless Phase 1 fails entirely** — in that case skip Phases 2-3 and report "Server unreachable."

---

## Phase 1 — Trigger (forces server start)

### Step 1: MCP server alive

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- If the tool returns a JSON result with capabilities listed: **provisional PASS** — report the number of capabilities. **Save the full result for use in Step 5.**
- If the tool errors or times out: **FAIL** — report the error.

**Inline validation** (required before confirming PASS):
1. Verify the result contains `cli_tools` with at least `ivy_check` and `ivyc` keys.
2. Verify `mcp_tool_count` is ≥ 10 (the expected minimum tool set).
3. Use Bash to confirm CLI tool presence matches the report:
   ```
   which ivy_check ivyc ivy_show 2>/dev/null | wc -l
   ```
   Compare the count against the `cli_tools` values. If there's a mismatch (e.g., capabilities says `ivy_check: true` but `which` says not found), downgrade to **WARN** — "MCP reports CLI tool availability inconsistent with PATH."

- If validation passes: promote to **PASS**.
- If validation finds inconsistency: **WARN** with details.

### Step 2: LSP responding

Use `LSP(operation="documentSymbol", filePath="<path_to_ivy_file>", line=1, character=1)` to request a document symbol list from any `.ivy` file in the workspace. If no `.ivy` file is known, use `Glob` to find one first (e.g., `**/*.ivy` under the protocol-testing directory).

- If the LSP returns a symbol list (even empty): **provisional PASS** — report the number of symbols.
- If the LSP times out or returns an error: **FAIL** — report the error message.

**Inline validation** (required before confirming PASS):
1. Use `Read` to open the same `.ivy` file and count lines that look like declarations (`type `, `relation `, `function `, `action `, `object `, `module `, `instance `).
2. The LSP symbol count should be in the same ballpark as the declaration count (±50% is acceptable — LSP may report sub-symbols). If the LSP returns 0 symbols but the file clearly has declarations, downgrade to **WARN** — "LSP returned 0 symbols but file has N declarations. Index may be incomplete."
3. Verify at least one symbol has a valid line number > 0.

- If validation passes: promote to **PASS**.
- If discrepancy found: **WARN** with details.

**Early exit**: If BOTH Step 1 AND Step 2 fail, skip Phases 2-3 entirely. Report: "Server unreachable — check installation and PATH. Run `ivy_lsp --help` to verify the binary is available."

### Phase 1 Review

Dispatch a `spec-analyst` agent with the following prompt:

> "Review the Phase 1 health check results for the Ivy LSP + MCP stack. You are given:
> - Step 1 result: [paste MCP capabilities result + inline validation outcome]
> - Step 2 result: [paste LSP documentSymbol result + inline validation outcome]
>
> Check for:
> 1. **False positives**: Did any step report PASS but the data looks wrong? (e.g., tool count is 0 but marked PASS, symbol list is suspiciously empty)
> 2. **Consistency**: Do Step 1 and Step 2 results agree? (e.g., if MCP reports 19 tools but LSP fails, something is split-brain)
> 3. **Missing signals**: Is there anything in the raw output that suggests a problem neither step caught?
>
> Report: CONFIRMED (results are trustworthy) or SUSPICIOUS (explain what looks wrong)."

If the reviewer reports SUSPICIOUS, add a **WARN** annotation to the affected steps and note the concern in the results table.

---

## Phase 2 — Validate infrastructure (now fresh)

### Step 3: LSP process alive

**Primary: PID tracking files.** Run via Bash:
```
for f in /tmp/ivy-lsp-pids/*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f")
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "ALIVE $(basename "$f") pid=$pid"
  else
    echo "STALE $(basename "$f") pid=$pid"
  fi
done
```

- **provisional PASS**: At least one tracked PID file reports ALIVE.
- **WARN**: Stale PID files exist alongside live ones (suggest cleanup), OR only untracked processes found (no PID files).
- **FAIL**: No live processes found. (Unlikely since Phase 1 succeeded.)

**Inline validation**:
1. For each ALIVE PID, use Bash to verify the process is actually an `ivy_lsp` process:
   ```
   ps -p <pid> -o command= 2>/dev/null | head -1
   ```
   The command should contain `ivy_lsp` or `ivy-lsp`. If the PID is alive but running something else, downgrade to **WARN** — "PID <pid> is alive but not an ivy_lsp process."
2. Count total ALIVE vs STALE. If stale > alive, add cleanup recommendation.

### Step 4: LSP log health

**Check log freshness.** Run via Bash:
```
python3 -c "import os,time; s=os.stat('/tmp/ivy-lsp-latest.log'); age=time.time()-s.st_mtime; print(f'age_seconds={int(age)}')"
```

**Count errors in recent lines only (NOT the entire file).** Run via Bash:
```
tail -50 /tmp/ivy-lsp-latest.log | grep -v -E '\[SIGTERM\]|shutdown|write to closed|BrokenPipeError|ConnectionResetError|interpreter shutdown' | grep -c -E 'CRITICAL|Traceback'
```

**Count include_resolver errors in recent lines.** Run via Bash:
```
tail -200 /tmp/ivy-lsp-latest.log | grep -c "include_resolver ERROR"
```

**Shutdown noise filter**: Lines matching any of the following patterns are benign session teardown artifacts and MUST NOT cause a FAIL: `[SIGTERM]`, `shutdown`, `write to closed`, `BrokenPipeError`, `ConnectionResetError`, `interpreter shutdown`.

Classification:
- If the log file does not exist: **FAIL** — "Log file /tmp/ivy-lsp-latest.log not found."
- If non-shutdown CRITICAL/Traceback count (from `tail -50`) > 0: **FAIL** — quote the relevant non-shutdown line(s).
- If include_resolver ERROR count (from `tail -200`) > 10: **WARN** — "Include resolver has N errors in recent entries."
- If log age > 300 seconds but Phase 1 shows LSP is alive: **WARN** — "Log is stale (Ns old) but LSP responded. Symlink may point to a prior instance's log."
- Otherwise: **provisional PASS** — "No critical errors in recent log entries."

**Inline validation**:
1. Use `Grep` to search the log for the session's indexing milestone:
   ```
   Grep(pattern="Indexed.*files.*symbols", path="/tmp/ivy-lsp-latest.log", output_mode="content", head_limit=3)
   ```
   Verify the log contains a recent "Indexed N files, M symbols" line. If absent, downgrade to **WARN** — "No indexing milestone found in log. Server may not have completed initialization."
2. Verify the log's PID matches one of the ALIVE PIDs from Step 3 (use `Grep` for the PID in the log filename or content). If mismatch: **WARN** — "Log belongs to a different process than the live PID."

### Step 5: Layer staging active

**Primary: Use MCP capabilities data from Step 1.** Extract `staging_health` from the `ivy_capabilities` result already obtained in Step 1. If Step 1 failed, skip to the fallback.

Report: `layers_active`, `layer_count`, `total_staged`, `files_mapped_to_layers`.

Classification:
- If `staging_health.layers_active` is `true`: **provisional PASS** — report layer_count and total_staged.
- If `staging_health.layers_active` is `false` but `total_staged > 0`: **WARN** — "Flat staging (no layers) with N staged files."
- If `staging_health.source` is `"workspace_config_fallback"`: **WARN** — "Staging not built yet. Layer config found in .ivyworkspace (N layers defined). Staging builds after first file analysis."
- If `staging_health.symlink_failures > 0`: **WARN** — "N symlink failures detected in staging."
- If Step 1 failed (no capabilities data): **WARN** — "Layer staging status unknown."

**Inline validation** (required for PASS):
1. Use `Read` to open the active protocol's `.ivyworkspace` file (e.g., `protocol-testing/quic/.ivyworkspace`).
2. Parse the `workspace_layers` array and count layers.
3. Compare the layer count from `.ivyworkspace` against `staging_health.layer_count`. They should match. If mismatch: **WARN** — "staging_health reports N layers but .ivyworkspace defines M."
4. Verify layer IDs in staging_health match the `id` fields in `.ivyworkspace`.

### Phase 2 Review

Dispatch a `spec-analyst` agent with the following prompt:

> "Review the Phase 2 infrastructure validation results for the Ivy LSP + MCP stack. You are given:
> - Step 3 result: [PID check + inline validation]
> - Step 4 result: [log health + inline validation]
> - Step 5 result: [staging health + inline validation]
> - Phase 1 context: [Step 1-2 results for cross-reference]
>
> Check for:
> 1. **False positives**: Does a PASS step have suspicious data? (e.g., PID alive but log shows crash, staging reports 0 files mapped)
> 2. **Cross-phase consistency**: Do Phase 2 infrastructure results match Phase 1 functional results? (e.g., if Phase 1 LSP responded but Phase 2 finds no live PID, something is wrong)
> 3. **Staleness**: Are any results from a previous session rather than the current one? (check timestamps, PIDs, log freshness)
>
> Report: CONFIRMED or SUSPICIOUS (explain what looks wrong)."

If the reviewer reports SUSPICIOUS, add **WARN** annotations and note concerns.

---

## Phase 3 — Deep functional checks

### Step 6: Workspace access

Use `Glob` to find any `.ivy` file in the workspace. Then call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: the path to the found `.ivy` file
- `mode`: `"structural"`

- If the tool returns a result (even with diagnostics): **provisional PASS** — report the file and diagnostic count.
- If no `.ivy` files exist in the workspace: **FAIL** — "No .ivy files found in workspace."
- If the tool errors: **FAIL** — report the error.

**Inline validation**:
1. Use `Read` to open the same `.ivy` file. Verify it starts with `#lang ivy1.7` (or another valid `#lang` header).
2. If diagnostics reported 0 issues, do a quick sanity check: use `Grep` to search for `include ` lines in the file. If the file has includes, verify the diagnostic result didn't silently skip include resolution (which would hide errors). A file with 5+ includes and 0 diagnostics is likely correct; note it as validated.
3. If diagnostics reported issues, verify at least one reported diagnostic references a real line in the file (use `Read` to check the line number exists).

### Step 7: Coverage pipeline

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with `mode=stats` to test that the model analysis pipeline works.

- If the tool returns stats or coverage data: **provisional PASS** — report a summary (e.g., number of requirements, coverage percentage).
- If the tool errors: **FAIL** — report the error.

**Inline validation**:
1. Use `Glob` to find the requirements manifest file (e.g., `protocol-testing/quic/rfc9000_requirements.yaml`).
2. Use `Read` to open the manifest and count the total requirements listed.
3. Compare the manifest requirement count against the `ivy_coverage` total. They should match (or be very close). If mismatch > 10%: **WARN** — "Coverage reports N requirements but manifest has M."
4. Verify the coverage breakdown by level (MUST/SHOULD/MAY) sums to the total.

### Step 8: Cross-file resolution

Use the IDE LSP `goToDefinition` on a known symbol in an `.ivy` file. If no symbol is known, pick one from the symbol list obtained in Step 2.

- If the LSP returns a definition location (file + line): **provisional PASS** — report the target location.
- If the LSP returns no results or errors: **FAIL** — report the issue.

**Inline validation**:
1. Use `Read` to open the target file at the reported line number.
2. Verify the line actually contains a declaration of the symbol (e.g., if goToDefinition resolved `pkt_num` to `quic_types.ivy:57`, read line 57 and confirm it contains `pkt_num`).
3. If the line doesn't match the symbol: **FAIL** — "goToDefinition returned line N but the symbol is not there. LSP index may be stale."

### Step 9: Cross-layer include resolution

Use LSP `goToDefinition` on a symbol that requires cross-directory include resolution. Find a file in a subdirectory that includes a file from a different subdirectory (e.g., `quic_attacks_stack/*.ivy` including `quic_types` from `quic_stack/`).

- If the LSP returns a definition in a different directory: **provisional PASS**
- If the LSP returns no results: **FAIL** — "Cross-directory resolution is broken. Check layer staging."

**Inline validation**:
1. Confirm the source file and target file are in **different directories** (extract directory paths and compare).
2. Use `Read` to verify the source file has an `include` line that references the target module (e.g., `include quic_types`).
3. Use `Read` to verify the target file at the resolved line contains the expected symbol declaration.
4. If directories are the same: downgrade to **WARN** — "Resolution worked but source and target are in the same directory. This doesn't test cross-layer resolution. Try a different symbol."

### Phase 3 Review

Dispatch a `spec-analyst` agent with the following prompt:

> "Review the Phase 3 deep functional check results for the Ivy LSP + MCP stack. You are given:
> - Step 6 result: [workspace diagnostics + inline validation]
> - Step 7 result: [coverage stats + inline validation]
> - Step 8 result: [cross-file resolution + inline validation]
> - Step 9 result: [cross-layer resolution + inline validation]
> - Phase 1-2 context: [previous step results for cross-reference]
>
> Check for:
> 1. **False positives**: Did any deep check pass but the inline validation data suggests it shouldn't? (e.g., goToDefinition returned a location but the symbol isn't actually there)
> 2. **Coverage completeness**: Do the coverage stats make sense for the workspace? (e.g., 0% coverage with 97 requirements tracked — is that expected or suspicious?)
> 3. **Resolution quality**: For Steps 8-9, did the resolution actually demonstrate cross-file/cross-layer capability, or did it resolve within the same file/directory?
> 4. **Overall coherence**: Do all 9 steps tell a consistent story? (e.g., if coverage pipeline works but diagnostics fail, something is inconsistent)
>
> Report: CONFIRMED or SUSPICIOUS (explain what looks wrong)."

If the reviewer reports SUSPICIOUS, add **WARN** annotations and note concerns.

---

## Result Presentation

Present the final results in this format. Add a **Validated** column to show inline validation status:

```
## Ivy LSP + MCP Health Check

| # | Check                    | Status | Validated | Details                          |
|---|--------------------------|--------|-----------|----------------------------------|
| 1 | MCP server alive         | PASS   | Yes       | 19 tools, 3 CLI tools (PATH OK)  |
| 2 | LSP responding           | PASS   | Yes       | 37 symbols (file has ~30 decls)  |
|   | **Phase 1 Review**       | OK     | —         | Confirmed by spec-analyst        |
| 3 | LSP process alive        | PASS   | Yes       | PID 12345 (ivy_lsp confirmed)    |
| 4 | LSP log health           | PASS   | Yes       | No errors, indexing milestone OK  |
| 5 | Layer staging active     | PASS   | Yes       | 2 layers (matches .ivyworkspace) |
|   | **Phase 2 Review**       | OK     | —         | Confirmed by spec-analyst        |
| 6 | Workspace access         | PASS   | Yes       | quic_types.ivy — 0 diagnostics   |
| 7 | Coverage pipeline        | PASS   | Yes       | 97 reqs (matches manifest)       |
| 8 | Cross-file resolution    | PASS   | Yes       | pkt_num → quic_types.ivy:57 ✓    |
| 9 | Cross-layer resolution   | PASS   | Yes       | cid → quic_stack/ from attacks/  |
|   | **Phase 3 Review**       | OK     | —         | Confirmed by spec-analyst        |

**Overall: 9/9 PASS (3/3 phase reviews confirmed)**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If any checks FAIL → Gate**:
- Ask: "Health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options.
- Wait for user selection before showing suggested actions for that check.

**If all checks PASS → Inform-and-Continue**:
- State: "All 9 checks pass, all 3 phase reviews confirmed. System is healthy. Run `/nct-validate` for deeper correctness testing?"

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Health check passed with {N} warning(s): {list}. Any concern, or good to proceed?"

**If any phase review reports SUSPICIOUS → Gate**:
- State: "Phase N review flagged suspicious results: {details}. Investigate before proceeding?"

If any checks fail, add a `### Suggested Actions` section at the end:

- If Step 1 fails: "The MCP server is not reachable. Check the plugin configuration and `ivy_lsp --help`."
- If Step 2 fails: "The LSP process may be running but unresponsive. Try restarting it."
- If Step 3 fails: "Stale PID files found. Clean up with `rm /tmp/ivy-lsp-pids/*.pid`."
- If Step 4 fails: "Inspect `/tmp/ivy-lsp-latest.log` for crash details. Consider restarting the LSP."
- If Step 5 warns: "Layer staging is not active. Ensure `.ivyworkspace` has `workspace_layers` defined."
- If Step 6 fails: "Ensure `.ivy` files exist in the workspace and the MCP server has read access."
- If Step 7 fails: "Model analysis failed. This may indicate a missing or corrupt protocol model."
- If Step 8 fails: "Cross-file resolution is not working. The LSP index may need rebuilding."
- If Step 9 fails: "Cross-directory resolution is broken. Check layer staging and `.ivyworkspace` configuration."

See the `tooling-reference` skill for LSP and MCP architecture.
