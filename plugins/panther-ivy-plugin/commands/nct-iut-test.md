---
name: nct-iut-test
description: Run an Ivy test against an IUT via PANTHER's experiment pipeline
arguments:
  - name: protocol
    description: Protocol name (e.g., "bgp", "quic")
    required: true
  - name: test_name
    description: Ivy test file name without .ivy extension (e.g., "bgp_speaker_test_join")
    required: true
  - name: iut_name
    description: Registered IUT plugin name (e.g., "frr_bgp")
    required: true
  - name: version
    description: Protocol version (default uses protocol's default)
    required: false
  - name: timeout
    description: Total timeout in seconds (default 120)
    required: false
---
<purpose>
Shortcut command. Directly calls `ivy_iut_test` against a compiled Ivy
test binary and a real Implementation Under Test via PANTHER's experiment
pipeline. For guided testing with failure diagnosis, use the `verify`
workflow.
</purpose>

<journal-note>
Per `.claude/rules/journaling-contract.md` §1, this command writes the
journal via the underlying `experiment-ops` skill on the IUT execution path
(the `posttooluse/gates/run-gate.py --id g5` PostToolUse hook also appends
`gate_dispatched` for G5 trace analysis, per contract §3). The terminal-state HARD-GATE
in contract §5 binds the dispatched agent.
</journal-note>

<metadata mode="FAST"
          orchestrator="false"
          workspace-aware="true"/>

## Instructions

<instructions>
  <step n="1">Accept the arguments. If required arguments are missing, ask the user: protocol ("Which protocol? e.g., bgp, quic"), test_name ("Which test? e.g., bgp_speaker_test_join"), iut_name ("Which IUT implementation? e.g., frr_bgp").</step>
  <step n="2">Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test` with `protocol`, `test_name`, `iut_name`; include `version` and `timeout` only if supplied.</step>
  <step n="3">Parse the JSON result (`verdict`, `test_name`, `iut_name`, `protocol`, `test_stdout`, `test_stderr`, `iut_logs`, `duration_seconds`, `output_dir`, `experiment_summary`, `error`).</step>
  <step n="4">Present results using the outcome templates below.</step>
</instructions>

<outcome verdict="PASS">
<severity class="tool-outcome" value="PASS"/>
```
## IUT Test Result: PASS

**Test:** {test_name}
**IUT:** {iut_name}
**Protocol:** {protocol}
**Duration:** {duration_seconds}s

Test executed successfully against the IUT.

**Output directory:** {output_dir}
```
</outcome>

<outcome verdict="FAIL">
<severity class="tool-outcome" value="FAIL"/>
```
## IUT Test Result: FAIL

**Test:** {test_name}
**IUT:** {iut_name}
**Protocol:** {protocol}
**Duration:** {duration_seconds}s

### Test Logs
{iut_logs}

### Experiment Summary
{Format experiment_summary test results: status, error_message if any}

**Output directory:** {output_dir}

### Suggested Actions
- Inspect the full output: `Read {output_dir}/experiment_summary.json`
- Check IUT logs: `Read {output_dir}/{test_subdir}/test.log`
- Use the `verify` workflow for guided failure diagnosis
```
</outcome>

<outcome verdict="FAIL" subtype="error-or-timeout">
<severity class="tool-outcome" value="FAIL"/>
```
## IUT Test Result: {verdict upper}

**Test:** {test_name}
**IUT:** {iut_name}

### Error
{error}

### Suggested Actions
- Check Docker is running: `docker ps`
- Verify IUT plugin exists: check `panther/plugins/services/iut/{protocol}/{iut_name}/`
- Try compiling first: `/nct-compile {test_file}`
```
</outcome>

**IMPORTANT**: Do NOT run `panther run` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test`. The MCP tool wraps `panther run` with structured output, error-coded failures, and test-result JSON that the PostToolUse render hook formats per the active workflow; direct `panther run` returns raw stdout the render hook cannot reshape.

On an `InputValidationError` from `ivy_iut_test` (deferred-tool schema not loaded, MCP server unavailable), follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md`: one retry via `ToolSearch({query: "select:ivy_iut_test"})`, then AskUserQuestion with triage / skip / abandon options.
