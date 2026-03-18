---
name: nct-health
description: Run a health check sequence for the Ivy LSP + MCP integration
arguments: []
---

Run a comprehensive health check of the Ivy LSP and MCP integration stack, reporting PASS/FAIL for each step.

## Instructions

Run the following 9 checks in order. For each check, record PASS, WARN, or FAIL with a short detail message. If a check fails, continue with the remaining checks (do not abort early).

### Step 1: LSP process alive

Run via Bash:
```
pgrep -f ivy_lsp
```

- If exit code is 0 and PIDs are returned: **PASS** -- report the PID(s).
- If more than 6 PIDs are returned: **WARN** -- "N ivy_lsp processes running. Consider killing stale instances with `pkill -f ivy_lsp`."
- If exit code is non-zero or no output: **FAIL** -- "No ivy_lsp process found."

### Step 2: LSP log health

Run via Bash:
```
tail -50 /tmp/ivy-lsp-latest.log
```

Also run:
```
grep -c "include_resolver ERROR" /tmp/ivy-lsp-latest.log
```

Also run:
```
grep -c "CRITICAL\|Traceback" /tmp/ivy-lsp-latest.log
```

- If the file does not exist: **FAIL** -- "Log file /tmp/ivy-lsp-latest.log not found."
- If CRITICAL/Traceback count > 0: **FAIL** -- "Log contains N critical errors. Run `grep CRITICAL /tmp/ivy-lsp-latest.log` for details."
- If include_resolver ERROR count > 10: **WARN** -- "Include resolver has N errors. Layer routing may be broken."
- If the last 50 lines contain `CRITICAL` or `Traceback` or `crash`: **FAIL** -- quote the relevant line(s).
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

Use `Glob` to find any `.ivy` file in the workspace. Then call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: the path to the found `.ivy` file

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

Run via Bash:
```
grep -c "Layered staging active\|Skipping scope-based partitioned staging" /tmp/ivy-lsp-latest.log
```

- If count > 0: **PASS** -- "Layer staging active"
- If count = 0: **WARN** -- "Layer staging may not be initialized. Check workspace_layers in .ivyworkspace and restart the LSP."

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
