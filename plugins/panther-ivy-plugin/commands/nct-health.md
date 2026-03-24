---
name: nct-health
description: Run a health check sequence for the Ivy LSP + MCP integration
arguments: []
---
<!-- MODE: FAST — Diagnostic health check, no orchestrator required -->

Run a comprehensive health check of the Ivy LSP and MCP integration stack, reporting PASS/FAIL for each step.

## Instructions

**Workspace Status**: Before running checks, call `ivy_workspace(action="get")` to confirm the active workspace. Report the current workspace state as a preliminary line in the results table (e.g., "Active workspace: quic" or "No workspace active").

Run the following 9 checks in order. For each check, record PASS, WARN, or FAIL with a short detail message. If a check fails, continue with the remaining checks (do not abort early).

### Step 1: LSP process alive

**Primary: PID tracking files.** Run via Bash:
```
for f in /tmp/ivy-lsp-pids/*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then
    echo "ALIVE $(basename "$f") pid=$pid"
  else
    echo "STALE $(basename "$f") pid=$pid"
  fi
done
```

**Fallback: pgrep** (catches untracked instances). Run via Bash:
```
pgrep -f ivy_lsp
```

Classification:
- **PASS**: At least one tracked `lsp-*` PID file reports ALIVE.
- **WARN**: Stale PID files exist alongside live ones (suggest cleanup), OR more than 6 total processes found, OR only untracked processes found via pgrep (no PID files).
- **FAIL**: No live processes found by either method.

### Step 2: LSP log health

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

**Shutdown noise filter**: Lines matching any of the following patterns are benign session teardown artifacts and MUST NOT cause a FAIL: `[SIGTERM]`, `shutdown`, `write to closed`, `BrokenPipeError`, `ConnectionResetError`, `interpreter shutdown`. These occur when LSP instances are killed at session end.

Classification:
- If the log file does not exist: **FAIL** -- "Log file /tmp/ivy-lsp-latest.log not found."
- If non-shutdown CRITICAL/Traceback count (from `tail -50`) > 0: **FAIL** -- quote the relevant non-shutdown line(s).
- If include_resolver ERROR count (from `tail -200`) > 10: **WARN** -- "Include resolver has N errors in recent entries. Layer routing may be broken."
- If log age > 300 seconds but Step 1 shows LSP is running: **WARN** -- "Log is stale (Ns old) but LSP is alive. Symlink may point to a prior instance's log."
- Otherwise: **PASS** -- "No critical errors in recent log entries."

### Step 3: LSP responding

Use `LSP(operation="documentSymbol", filePath="<path_to_ivy_file>", line=1, character=1)` to request a document symbol list from any `.ivy` file in the workspace. If no `.ivy` file is known, use `Glob` to find one first (e.g., `**/*.ivy`).

- If the LSP returns a symbol list (even empty): **PASS** -- report the number of symbols.
- If the LSP times out or returns an error: **FAIL** -- report the error message.

### Step 4: MCP server alive

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- If the tool returns a JSON result with capabilities listed: **PASS** -- report the number of capabilities.
- If the tool errors or times out: **FAIL** -- report the error.

### Step 5: Workspace access

Use `Glob` to find any `.ivy` file in the workspace. Then call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: the path to the found `.ivy` file
- `mode`: `"structural"`

- If the tool returns a result (even with diagnostics): **PASS** -- report the file and diagnostic count.
- If no `.ivy` files exist in the workspace: **FAIL** -- "No .ivy files found in workspace."
- If the tool errors: **FAIL** -- report the error.

### Step 6: Model builds

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with `mode=stats` to test that the model analysis pipeline works.

- If the tool returns stats or coverage data: **PASS** -- report a summary (e.g., number of requirements, coverage percentage).
- If the tool errors: **FAIL** -- report the error.

### Step 7: Cross-file resolution

Use the IDE LSP `goToDefinition` on a known symbol in an `.ivy` file. If no symbol is known, pick one from the symbol list obtained in Step 3.

- If the LSP returns a definition location (file + line): **PASS** -- report the target location.
- If the LSP returns no results or errors: **FAIL** -- report the issue.

### Step 8: Layer staging active

**Primary: Use MCP capabilities data from Step 4.** Extract `staging_health` from the `ivy_capabilities` result already obtained in Step 4. If Step 4 failed, skip to the fallback.

Report: `layers_active`, `layer_count`, `total_staged`, `files_mapped_to_layers`.

Classification:
- If `staging_health.layers_active` is `true`: **PASS** -- report layer_count and total_staged.
- If `staging_health.layers_active` is `false` but `total_staged > 0`: **WARN** -- "Flat staging (no layers) with N staged files. No collision risk but layer routing is inactive."
- If `staging_health.symlink_failures > 0`: **WARN** -- "N symlink failures detected in staging."
- If Step 4 failed (no capabilities data): fall back to log grep as secondary confirmation only.

**Fallback (secondary, only if Step 4 failed).** Run via Bash:
```
tail -200 /tmp/ivy-lsp-latest.log | grep -c "Layered staging active\|Skipping scope-based partitioned staging"
```
- If count > 0: **WARN** -- "Layer staging seen in log (MCP unavailable for authoritative check)."
- If count = 0: **WARN** -- "Layer staging status unknown. Check workspace_layers in .ivyworkspace and restart the LSP."

### Step 9: Cross-layer include resolution

Use LSP `goToDefinition` on a symbol that requires cross-directory include resolution.
Find a file in a subdirectory that includes a file from a different subdirectory
(e.g., `quic_attacks_stack/*.ivy` including `quic_types` from `quic_stack/`).

- If the LSP returns a definition in a different directory: **PASS**
- If the LSP returns no results: **FAIL** -- "Cross-directory resolution is broken. Check layer staging."

## Result Presentation

Present the final results in this format:

```
## Ivy LSP + MCP Health Check

| # | Check                    | Status | Details                          |
|---|--------------------------|--------|----------------------------------|
| 1 | LSP process alive        | PASS   | PID 12345                        |
| 2 | LSP log health           | PASS   | No critical errors               |
| 3 | LSP responding           | PASS   | 42 symbols returned              |
| 4 | MCP server alive         | PASS   | 12 capabilities                  |
| 5 | Workspace access         | PASS   | quic_types.ivy -- 0 diagnostics  |
| 6 | Model builds             | PASS   | 15 requirements, 80% coverage    |
| 7 | Cross-file resolution    | PASS   | quic_frame.ivy:34                |
| 8 | Layer staging active     | PASS   | Layer staging active             |
| 9 | Cross-layer resolution   | PASS   | quic_types resolved from attacks |

**Overall: 9/9 PASS**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If any checks FAIL → Gate**:
- Ask: "Health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options (e.g., "1. LSP process alive  2. Cross-layer resolution").
- Wait for user selection before showing suggested actions for that check.

**If all checks PASS → Inform-and-Continue**:
- State: "All 9 checks pass. System is healthy. Run `/nct-validate` for deeper correctness testing?"
- No gate needed.

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Health check passed with {N} warning(s): {list}. Any concern, or good to proceed?"
- Continue unless the user wants to discuss.

If any checks fail, add a `### Suggested Actions` section at the end:

- If Step 1 fails: "Start the Ivy LSP server. Check if `ivy_lsp` is installed and in PATH."
- If Step 2 fails: "Inspect `/tmp/ivy-lsp-latest.log` for crash details. Consider restarting the LSP."
- If Step 3 fails: "The LSP process may be running but unresponsive. Try restarting it."
- If Step 4 fails: "The MCP server is not reachable. Check the plugin configuration in `.claude/plugins.json`."
- If Step 5 fails: "Ensure `.ivy` files exist in the workspace and the MCP server has read access."
- If Step 6 fails: "Model analysis failed. This may indicate a missing or corrupt protocol model."
- If Step 7 fails: "Cross-file resolution is not working. The LSP index may need rebuilding."
- If Step 8 warns: "Layer staging is not active. Ensure `.ivyworkspace` has `workspace_layers` defined."
- If Step 9 fails: "Cross-directory resolution is broken. Check layer staging and `.ivyworkspace` configuration."

See the `tooling-reference` skill for LSP and MCP architecture.
