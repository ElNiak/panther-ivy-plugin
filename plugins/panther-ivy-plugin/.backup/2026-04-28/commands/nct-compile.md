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
<purpose>
Shortcut command. Directly calls `ivy_compile` on a single file. For
guided compilation within a build cycle, use the `build` workflow.
</purpose>

<metadata mode="FAST"
          orchestrator="false"
          workspace-aware="true"
          note="Active workspace scopes include resolution. Use /set-workspace &lt;protocol&gt; if not set. Prefer running /nct-check on the file first."/>

## Instructions

<instructions>
  <step n="1">Accept the file path argument. If no file is provided, ask the user which .ivy file to compile.</step>
  <step n="2">Determine the target: use the `target` argument if provided, otherwise default to `"test"`.</step>
  <step n="3">Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` with `relative_path`, `target`, and `isolate` (if supplied).</step>
  <step n="4">Parse the JSON result (`success`, `output`, `target`, `duration_seconds`).</step>
  <step n="5">Present results using the outcome templates below.</step>
</instructions>

<outcome verdict="PASS">
<severity class="tool-outcome" value="PASS"/>
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
</outcome>

<outcome verdict="FAIL">
<severity class="tool-outcome" value="FAIL"/>
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
</outcome>

**IMPORTANT**: Do NOT run `ivyc` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile`.

On an `InputValidationError` from `ivy_compile` (deferred-tool schema not loaded, MCP server unavailable), follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md`: one retry via `ToolSearch({query: "select:ivy_compile"})`, then AskUserQuestion with triage / skip / abandon options.

See the `methodology` knowledge skill for compilation troubleshooting.
