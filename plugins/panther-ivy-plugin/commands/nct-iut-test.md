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
> **Shortcut command** — directly calls `ivy_iut_test`. For guided testing with failure diagnosis, use the `verify` workflow.

<!-- MODE: FAST — Single IUT test run, no orchestrator required -->

Run an Ivy test binary against a real Implementation Under Test (IUT) via PANTHER's experiment pipeline.

## Instructions

1. Accept the arguments. If required arguments are missing, ask the user:
   - protocol: "Which protocol? (e.g., bgp, quic)"
   - test_name: "Which test? (e.g., bgp_speaker_test_join)"
   - iut_name: "Which IUT implementation? (e.g., frr_bgp)"

2. Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test` with:
   - `protocol`: the provided protocol
   - `test_name`: the provided test name
   - `iut_name`: the provided IUT name
   - `version`: the version argument if provided, otherwise omit
   - `timeout`: the timeout argument if provided (as integer), otherwise omit

3. Parse the JSON result containing `verdict`, `test_name`, `iut_name`, `protocol`, `test_stdout`, `test_stderr`, `iut_logs`, `duration_seconds`, `output_dir`, `experiment_summary`, and `error`.

4. Present results in this structured format:

### If verdict is "pass":
```
## IUT Test Result: PASS

**Test:** {test_name}
**IUT:** {iut_name}
**Protocol:** {protocol}
**Duration:** {duration_seconds}s

Test executed successfully against the IUT.

**Output directory:** {output_dir}
```

### If verdict is "fail":
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

### If verdict is "error" or "timeout":
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

**IMPORTANT**: Do NOT run `panther run` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test`. The MCP tool wraps `panther run` with structured output, error-coded failures, and test-result JSON that the PostToolUse render hook formats per the active workflow; direct `panther run` returns raw stdout the render hook cannot reshape.

On an `InputValidationError` from `ivy_iut_test` (deferred-tool schema not loaded, MCP server unavailable), follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md`: one retry via `ToolSearch({query: "select:ivy_iut_test"})`, then AskUserQuestion with triage / skip / abandon options.
