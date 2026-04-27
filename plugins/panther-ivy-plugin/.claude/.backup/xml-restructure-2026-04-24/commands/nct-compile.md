---
name: nct-compile
description: Compile an Ivy model to a test binary via ivy-tools
arguments:
  - name: file
    description: Path to the .ivy file to compile (relative to project root)
    required: true
  - name: target
    description: Compilation target (default "test")
    required: false
  - name: isolate
    description: Optional isolate name to compile specifically
    required: false
---
> **Shortcut command** — directly calls `ivy_compile`. For guided compilation within a build cycle, use the `build` workflow.

<!-- MODE: FAST — Single-file compilation, no orchestrator required -->
<!-- Warn if file has not been verified with /nct-check first -->

Compile the specified Ivy model to a test executable using ivy-tools.

<!-- Workspace: Active workspace scopes include resolution for compilation. Use /set-workspace <protocol> if not already set. -->

## Instructions

1. Accept the file path argument. If no file is provided, ask the user which .ivy file to compile.

2. Determine the target:
   - If `target` argument provided, use it
   - Otherwise default to `"test"`

3. Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` with:
   - `relative_path`: the provided file path
   - `target`: the compilation target
   - `isolate`: the isolate argument if provided, otherwise omit

4. Parse the JSON result containing `success`, `output`, `target`, and `duration_seconds`.

5. Present results in this structured format:

### If success is true (SUCCESS):
```
## Compilation Result: SUCCESS

**File:** {file_path}
**Target:** {target}
**Isolate:** {isolate or "all"}

Test binary compiled successfully.
The executable can be found in the build/ directory.

### Next Steps
- Run the test binary against an IUT via PANTHER experiment framework
- Use `/nct-check` to verify formal properties before running
```

### If success is false (FAILURE):
```
## Compilation Result: FAILURE

**File:** {file_path}
**Target:** {target}

### Errors
{Parse output for specific error messages}

### Suggested Actions
- Run `/nct-check {file}` first to verify formal properties
- Use Claude's `Read` tool to check file structure
- Check for missing includes or undefined symbols
```

**IMPORTANT**: Do NOT run `ivyc` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile`.

On an `InputValidationError` from `ivy_compile` (deferred-tool schema not loaded, MCP server unavailable), follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md`: one retry via `ToolSearch({query: "select:ivy_compile"})`, then AskUserQuestion with triage / skip / abandon options.

See the `methodology-reference` knowledge skill for compilation troubleshooting.
