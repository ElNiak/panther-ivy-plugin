---
name: nct-serena-health
description: Validate the Serena integration chain (serena-mcp-server -> SolidLSP -> IvyLanguageServer -> ivy_lsp)
arguments: []
---
<!-- MODE: FAST — Diagnostic health check, no orchestrator required -->

Validate the full Serena integration layer end-to-end by probing the running MCP server. Serena runs in its own isolated `.venv` managed by `start-serena.sh`, so all checks go through MCP rather than the ambient shell environment.

## Instructions

Run the following 7 checks organized in 3 layers. Execution is **strictly sequential with interleaved verification** (verify-as-you-go).

### Execution Model

**Every step follows this 3-phase cycle:**
1. **Call** — invoke one tool (Serena MCP, Read, Grep, or Glob)
2. **Verify** — immediately verify the result using classical tools (Read, Grep, Glob). Do NOT proceed until verification is complete.
3. **Record** — log PASS/WARN/FAIL with verification evidence, then proceed to the next step.

**Do NOT batch multiple tool calls in a single message.** Each step must complete before starting the next.

**Gate rule**: If Step 1 FAILs → abort with "Serena MCP server is not running." and show suggested actions. All subsequent steps depend on a live server.

---

## Layer 1: Server Liveness — "Is the Serena MCP server alive?"

### Step 1: Serena MCP server alive

Call `mcp__plugin_panther-ivy-plugin_serena__get_current_config` with no arguments.

Classification:
- **PASS**: Returns config JSON. Extract and report: project name, serena version (if present), active tool count, configured languages.
- **FAIL**: "Serena MCP server not responding." Report the error. **Abort all remaining steps.**

### Step 2: Ivy tools registered

From the config result in Step 1, inspect the active tools list. Look for the 4 Ivy-specific **Serena integration tools**: `ivy_diagnostics`, `ivy_goto_definition`, `ivy_server_status`, `ivy_test_scope`.

These are Serena-layer tools (classes in `serena/tools/ivy_tools.py`) that bridge the Ivy LSP into Serena's MCP interface. They are distinct from the ivy-lsp MCP tools (`ivy_verify`, `ivy_compile`, `ivy_model_info`) validated by `/nct-health`.

Classification:
- **PASS**: All 4 Ivy tools found in the active tool list. Report tool names.
- **WARN**: Some Ivy tools missing. "Ivy tools are defined but may be disabled (ToolMarkerOptional). Add them to `included_optional_tools` in `.serena/project.yml`."
- **FAIL**: No Ivy tools found. "Ivy language support may not be configured in `.serena/project.yml`."

---

## Layer 2: Configuration — "Is it correctly configured?"

### Step 3: Serena project config

Use `Glob` to find `.serena/project.yml` at the workspace root (the panther_ivy directory). Then use `Read` to inspect it.

Check:
1. File exists and is valid YAML
2. `ivy` is in the languages list — this IS required, because this project.yml configures the Ivy workspace that Serena operates on
3. `included_optional_tools` contains the 4 Ivy tools from Step 2

Classification:
- **PASS**: project.yml exists, ivy in languages, all 4 tools in `included_optional_tools`. Report configured languages and tools.
- **WARN**: ivy in languages but some tools missing from `included_optional_tools`. "Add missing tools to enable full Ivy integration."
- **FAIL**: "project.yml not found, unparseable, or ivy not in languages list."

### Step 4: Workspace environment

From the Step 1 config result, extract the project root / workspace path. Verify it points to the panther_ivy directory (should contain `protocol-testing/` and `.serena/project.yml`).

**Classical verify**: Use `Glob` to confirm the project root contains expected markers:
```
Glob(pattern="protocol-testing/", path="<project_root>")
Glob(pattern=".serena/project.yml", path="<project_root>")
```

Classification:
- **PASS**: Project root contains `protocol-testing/` and `.serena/project.yml`. Report the path.
- **WARN**: Project root is unexpected or missing expected markers. "Serena may be running against the wrong workspace."

---

## Layer 3: Integration — "Does the full Serena → LSP chain work?"

### Step 5: LSP handshake through Serena

Call `mcp__plugin_panther-ivy-plugin_serena__get_symbols_overview` with:
- `relative_path`: path to an `.ivy` file in the workspace (use `Glob` to find one first, e.g. `**/sample.ivy` or `**/quic_types.ivy`)

**Classical verify**: Use `Read` to open the same file and count lines that look like declarations (`type `, `relation `, `function `, `action `, `object `, `module `). The symbol count should be in the same ballpark (±50%).

Classification:
- **PASS**: Returns symbols matching file content. Report symbol count and file.
- **WARN**: Empty symbols returned. "Language server may not have indexed the file yet. Try waiting 10-15 seconds and re-running."
- **FAIL**: "Serena could not retrieve symbols via LSP." Report the error.

### Step 6: Serena file operations

Call `mcp__plugin_panther-ivy-plugin_serena__read_file` with the same `.ivy` file used in Step 5.

**Classical verify**: Use `Read` to open the file directly and compare the first 10 lines of content. They should match exactly.

Classification:
- **PASS**: Content matches direct file read.
- **FAIL**: "Serena cannot read files in the workspace." Report the discrepancy.

### Step 7: Cross-validate with /nct-health

Check if `/nct-health` was run earlier in this session (look for its result table in the conversation).

If found:
- Compare MCP server status (nct-health Step 1) with Serena's MCP status (this command Step 1) — both should show healthy servers
- Compare LSP process status (nct-health Step 3) with Serena's LSP view (this command Step 5) — both should show functional LSP
- Compare workspace state consistency

Classification:
- **PASS**: Results are consistent, or /nct-health was not run.
- **WARN**: Inconsistency detected. Detail the mismatch.

---

## Result Presentation

Present the final results in this format:

```
## Serena Integration Health Check

### Layer 1: Server Liveness
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 1 | Serena MCP server alive   | PASS   | project: panther-ivy, 24 tools       |
| 2 | Ivy tools registered      | PASS   | 4/4 ivy tools active                 |

### Layer 2: Configuration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 3 | Serena project config     | PASS   | languages: ivy, 4 tools included     |
| 4 | Workspace environment     | PASS   | /path/to/panther_ivy (verified)      |

### Layer 3: Integration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 5 | LSP handshake via Serena  | PASS   | 12 symbols in quic_types.ivy         |
| 6 | Serena file operations    | PASS   | Content matches direct read           |
| 7 | Cross-validate /nct-health| PASS   | /nct-health not run (skipped)        |

**Overall: 7/7 PASS**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If Step 1 FAILs → Gate (abort)**:
- State: "Serena MCP server is not running. See suggested actions below."
- Do NOT proceed to Steps 2-7.

**If other checks FAIL → Gate**:
- Ask: "Serena health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options.
- Wait for user selection before showing suggested actions.

**If all checks PASS → Inform-and-Continue**:
- State: "Serena integration is healthy. All 7 checks pass. Run `/nct-health` for full LSP + MCP validation?"

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Serena health check passed with {N} warning(s): {list}. Any concern?"

### Suggested Actions

If any checks fail, add a `### Suggested Actions` section:

- If Step 1 fails: "Serena MCP server not running. Check: (1) `PANTHER_IVY_ENABLE_SERENA=1` is set in environment, (2) `start-serena.sh` exists and `.mcp.json` references it, (3) `/tmp/serena-*.log` for startup errors, (4) panther-serena `.venv` exists at `submodules/panther-serena/.venv/` with `serena-mcp-server` binary."
- If Step 2 fails/warns: "Ivy tools not active. Add `ivy_diagnostics`, `ivy_goto_definition`, `ivy_server_status`, `ivy_test_scope` to `included_optional_tools` in `.serena/project.yml`. Ensure `ivy` is in the `languages` list."
- If Step 3 fails: "Create or fix `.serena/project.yml` at the panther_ivy workspace root. Ensure `ivy` is listed under `languages`."
- If Step 4 warns: "Serena is running against an unexpected workspace root. Check `start-serena.sh` workspace detection and `IVY_WORKSPACE_ROOT` env var."
- If Step 5 fails: "Serena cannot retrieve symbols via LSP. The IvyLanguageServer may not be starting. Check `/tmp/serena-*.log` for errors. Verify ivy_lsp is available inside the panther-serena `.venv`."
- If Step 6 fails: "Serena cannot read workspace files. Check file permissions and that the project root in Serena's config points to the correct directory."
- If Step 7 warns: "Inconsistency between `/nct-health` and `/nct-serena-health`. Run both again to confirm. If persistent, check whether ivy-lsp MCP and Serena MCP are pointing at the same workspace."

See the `tooling-reference` skill for Serena and LSP architecture details.
