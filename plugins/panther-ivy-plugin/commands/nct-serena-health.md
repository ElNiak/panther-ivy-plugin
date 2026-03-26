---
name: nct-serena-health
description: Validate the Serena integration chain (serena-mcp-server -> SolidLSP -> IvyLanguageServer -> ivy_lsp)
arguments: []
---
<!-- MODE: FAST — Diagnostic health check, no orchestrator required -->

Validate the full Serena integration layer end-to-end, from package installation through SolidLSP framework to IvyLanguageServer and the ivy_lsp binary.

## Instructions

Run the following 11 checks organized in 3 layers. Execution is **strictly sequential with interleaved verification** (verify-as-you-go).

### Execution Model

**Every step follows this 3-phase cycle:**
1. **Call** — invoke one tool (Bash or Serena MCP)
2. **Verify** — immediately verify the result using classical tools (Read, Grep, Glob, Bash). Do NOT proceed until verification is complete.
3. **Record** — log PASS/WARN/FAIL with verification evidence, then proceed to the next step.

**Do NOT batch multiple tool calls in a single message.** Each step must complete before starting the next.

**Gate rule**: If ALL of Steps 1-4 FAIL → abort with "Serena stack is not installed." Individual Layer 1 failures do NOT gate — continue collecting diagnostics.

---

## Layer 1: Prerequisites — "Is the Serena stack installed?"

### Step 1: serena-mcp-server binary

Run via Bash:
```
which serena-mcp-server
```

Classification:
- **PASS**: Binary found. Report the path.
- **FAIL**: "serena-mcp-server not found on PATH."

### Step 2: Serena package import

Run via Bash:
```
python3 -c "import serena; print(f'serena {serena.__version__}')" 2>&1
```

Classification:
- **PASS**: Import succeeds. Report the version.
- **FAIL**: "Serena package not importable." Report the error.

### Step 3: SolidLSP framework + Language.IVY

Run via Bash:
```
python3 -c "from solidlsp.ls_config import Language; print(f'Language.IVY = {Language.IVY}')" 2>&1
```

Classification:
- **PASS**: Prints `Language.IVY = ivy`. The Ivy enum is registered.
- **FAIL**: "SolidLSP not importable or Language.IVY not in enum."

### Step 4: IvyLanguageServer class loadable

Run via Bash:
```
python3 -c "from solidlsp.language_servers.ivy_language_server import IvyLanguageServer; print('IvyLanguageServer: OK')" 2>&1
```

Classification:
- **PASS**: Import succeeds.
- **FAIL**: "IvyLanguageServer not importable." Report the error.

### Step 5: DependencyProvider pattern

Run via Bash:
```
python3 -c "
from solidlsp.language_servers.ivy_language_server import IvyLanguageServer
has_provider = hasattr(IvyLanguageServer, '_create_dependency_provider')
has_inner = hasattr(IvyLanguageServer, 'DependencyProvider')
print(f'_create_dependency_provider: {has_provider}')
print(f'DependencyProvider inner class: {has_inner}')
if has_provider and has_inner:
    print('RESULT: DependencyProvider pattern OK')
else:
    print('RESULT: DependencyProvider pattern MISSING')
" 2>&1
```

Classification:
- **PASS**: Both `_create_dependency_provider` method and `DependencyProvider` inner class exist.
- **WARN**: One or both are missing. "IvyLanguageServer does not follow the DependencyProvider pattern. See adding_new_language_support_guide.md."

### Step 6: ivy_lsp binary

Run via Bash:
```
which ivy_lsp && ivy_lsp --version 2>&1 || echo "ivy_lsp not found"
```

Classification:
- **PASS**: Binary found. Report path and version.
- **FAIL**: "ivy_lsp not found on PATH. Install via: pip install ivy-lsp"

---

## Layer 2: Configuration — "Is it correctly configured?"

### Step 7: Serena project config

Use `Glob` to find `.serena/project.yml` at the workspace root (the panther_ivy directory). Then use `Read` to inspect it.

Check:
1. File exists and is valid YAML
2. Note what languages are listed (informational — ivy is NOT required here since project.yml configures the Serena project itself, not Ivy workspaces)

Classification:
- **PASS**: project.yml exists and is valid. Report configured languages.
- **WARN**: ivy not in languages list. "This is expected — project.yml configures Serena's own codebase, not the Ivy workspace."
- **FAIL**: "project.yml not found or unparseable."

---

## Layer 3: Integration — "Does the full chain work?"

### Step 8: Serena MCP server alive

Call `mcp__plugin_panther-ivy-plugin_serena__get_current_config` with no arguments.

Classification:
- **PASS**: Returns config JSON with project information. Report project name and active tools count.
- **FAIL**: "Serena MCP server not responding." Report the error.

### Step 9: Serena tool registry

From the config result in Step 8, inspect the active tools list. Look for tools containing "ivy" in their names (e.g., `ivy_diagnostics`, `ivy_goto_definition`, `ivy_server_status`, `ivy_test_scope`).

**Classical verify**: Run via Bash:
```
python3 -c "
from serena.tools.ivy_tools import IvyDiagnosticsTool, IvyGotoDefinitionTool, IvyServerStatusTool, IvyTestScopeTool
print('Ivy tools importable: 4 classes')
" 2>&1
```

Classification:
- **PASS**: Ivy tools found in registry AND importable. Report tool names.
- **WARN**: Tools importable but not in active registry. "Ivy tools are defined but may be disabled (ToolMarkerOptional). Add them to included_optional_tools in project.yml to enable."
- **FAIL**: "Ivy tools not importable." Report the error.

### Step 10: LSP handshake through Serena

Call `mcp__plugin_panther-ivy-plugin_serena__get_symbols_overview` with:
- `relative_path`: path to an `.ivy` file in the workspace (use `Glob` to find one first, e.g. `**/sample.ivy` or `**/quic_types.ivy`)

**Classical verify**: Compare the returned symbols with what you'd expect from the file content (use `Read` to check the file).

Classification:
- **PASS**: Returns symbols. Report symbol count and file.
- **WARN**: Empty symbols returned. "Language server may not have indexed the file yet. Try restarting."
- **FAIL**: "Serena could not retrieve symbols via LSP." Report the error.

### Step 11: Cross-validate with /nct-health

Check if `/nct-health` was run earlier in this session (look for its result table in the conversation).

If found:
- Compare LSP process status (nct-health Step 1) with Serena's view (this command Step 10)
- Compare ivy_lsp binary path from nct-health with Step 6 here

Classification:
- **PASS**: Results are consistent, or /nct-health was not run.
- **WARN**: Inconsistency detected. Detail the mismatch.

---

## Result Presentation

Present the final results in this format:

```
## Serena Integration Health Check

### Layer 1: Prerequisites
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 1 | serena-mcp-server binary  | PASS   | /path/to/serena-mcp-server           |
| 2 | Serena package import     | PASS   | serena 1.2.3                         |
| 3 | SolidLSP + Language.IVY   | PASS   | Language.IVY = ivy                   |
| 4 | IvyLanguageServer class   | PASS   | Import OK                            |
| 5 | DependencyProvider pattern| PASS   | Both attrs present                   |
| 6 | ivy_lsp binary            | PASS   | /path/to/ivy_lsp (v0.11.1)          |

### Layer 2: Configuration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 7 | Serena project config     | PASS   | languages: python, typescript        |

### Layer 3: Integration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 8 | Serena MCP server alive   | PASS   | project: serena, 24 tools active     |
| 9 | Serena tool registry      | PASS   | 4 ivy tools importable               |
|10 | LSP handshake via Serena  | PASS   | 5 symbols in sample.ivy              |
|11 | Cross-validate /nct-health| PASS   | /nct-health not run (skipped)        |

**Overall: 11/11 PASS**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If any checks FAIL → Gate**:
- Ask: "Serena health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options.
- Wait for user selection before showing suggested actions.

**If all checks PASS → Inform-and-Continue**:
- State: "Serena integration is healthy. All 11 checks pass. Run `/nct-health` for full LSP + MCP validation?"

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Serena health check passed with {N} warning(s): {list}. Any concern?"

### Suggested Actions

If any checks fail, add a `### Suggested Actions` section:

- If Step 1 fails: "Install Serena: `pip install -e <path-to-panther-serena>` or `uv pip install -e <path>`"
- If Step 2 fails: "Serena package not installed. Run: `pip install -e panther/plugins/services/testers/panther_ivy/submodules/panther-serena/`"
- If Step 3 fails: "SolidLSP not installed or Language.IVY not registered. Reinstall Serena or check ls_config.py."
- If Step 4 fails: "IvyLanguageServer import error. Check for syntax errors or missing dependencies in ivy_language_server.py."
- If Step 5 warns: "IvyLanguageServer does not use the DependencyProvider pattern. See .serena/memories/adding_new_language_support_guide.md."
- If Step 6 fails: "Install ivy-lsp: `pip install ivy-lsp` or `pip install -e <path-to-ivy-lsp>`"
- If Step 7 fails: "Create or fix .serena/project.yml at the workspace root."
- If Step 8 fails: "Serena MCP server not running. Check start-serena.sh and the plugin's .mcp.json configuration."
- If Step 9 warns: "Add ivy tools to included_optional_tools in .serena/project.yml. Or ensure ivy is in the languages list for the target project."
- If Step 10 fails: "Serena cannot retrieve symbols. The IvyLanguageServer may not be starting. Check /tmp/serena-*.log for errors."
- If Step 11 warns: "Inconsistency between /nct-health and /nct-serena-health. Run both again to confirm."

See the `tooling-reference` skill for Serena and LSP architecture details.
