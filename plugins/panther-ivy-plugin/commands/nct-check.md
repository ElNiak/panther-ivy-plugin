---
name: nct-check
description: Run formal verification on an Ivy specification file via ivy-tools
arguments:
  - name: file
    description: Path to the .ivy file to verify (relative to project root)
    required: true
  - name: isolate
    description: Optional isolate name to check specifically
    required: false
---

Run formal verification on the specified Ivy file using ivy-tools.

## Instructions

1. Accept the file path argument. If no file is provided, ask the user which .ivy file to verify.

2. Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with:
   - `relative_path`: the provided file path
   - `isolate`: the isolate argument if provided, otherwise omit

3. Parse the JSON result containing `success`, `diagnostics`, `diagnostic_count`, `raw_output`, and `duration_seconds`.

4. Present results in this structured format:

### If success is true (PASS):
```
## Verification Result: PASS

**File:** {file_path}
**Isolate:** {isolate or "all"}

All formal properties verified successfully.
- Isolate assumptions: OK
- Invariants: OK
- Safety properties: OK
```

### If success is false (FAIL):
```
## Verification Result: FAIL

**File:** {file_path}
**Isolate:** {isolate or "all"}

### Failures Detected
{Parse diagnostics array for specific error messages and list each one}

### Suggested Actions
- Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` to inspect the model structure
- Use Claude's `Grep` tool or native LSP go-to-definition to locate the failing symbol
- Check the behavior files for conflicting before/after monitors
```

**IMPORTANT**: Do NOT run `ivy_check` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`.

See the `workflow-reference` skill for verification debugging strategies.
