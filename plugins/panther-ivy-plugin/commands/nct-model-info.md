---
name: nct-model-info
description: Display the structure of an Ivy model via ivy-tools
arguments:
  - name: file
    description: Path to the .ivy file to inspect (relative to project root)
    required: true
  - name: isolate
    description: Optional isolate name to display information about
    required: false
---
<purpose>
Shortcut command. Directly calls `ivy_model_info` to display the model
structure (types, relations, functions, actions, invariants, isolates)
of the specified Ivy file. For model inspection within a review, use the
`review` workflow.
</purpose>

<metadata mode="FAST"
          orchestrator="false"
          workspace-aware="true"
          note="Active workspace provides scoped include resolution. Use /set-workspace &lt;protocol&gt; if not set."/>

## Instructions

<instructions>
  <step n="1">Accept the file path argument. If no file is provided, ask the user which .ivy file to inspect.</step>
  <step n="2">Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` with `relative_path` and `isolate` (if supplied).</step>
  <step n="3">Parse the JSON result (`success`, `output`, `duration_seconds`).</step>
  <step n="4">Present the model structure using the outcome template below. For large outputs, organize into collapsible sections or summarize with counts ("X types, Y relations, Z actions, W invariants").</step>
</instructions>

<outcome verdict="success">
<severity class="tool-outcome" value="PASS"/>
```
## Model Structure: {file_path}

**Isolate:** {isolate or "all"}

### Types
{List all type definitions from the output}

### Relations
{List all relation definitions}

### Functions
{List all function definitions}

### Actions
{List all action definitions with their signatures}

### Invariants
{List all invariant definitions}

### Isolates
{List all isolate definitions}
```
</outcome>

<outcome verdict="failure">
<severity class="tool-outcome" value="FAIL"/>
Present the error from `output`. Suggest `/nct-check {file}` to diagnose.
</outcome>

**IMPORTANT**: Do NOT run `ivy_show` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info`.

On an `InputValidationError` from `ivy_model_info` (deferred-tool schema not loaded, MCP server unavailable), follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md`: one retry via `ToolSearch({query: "select:ivy_model_info"})`, then AskUserQuestion with triage / skip / abandon options.

See the `ivy-toolkit` skill for `ivy_model_info` parameter details.
