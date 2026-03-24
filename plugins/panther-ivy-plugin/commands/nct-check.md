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
<!-- MODE: FAST — Single-file verification, no orchestrator required -->
<!-- For full methodology workflow, use /nct-scaffold instead -->

Run formal verification on the specified Ivy file using ivy-tools.

<!-- Workspace: Active workspace scopes include resolution for this file. Use /set-workspace <protocol> if not already set. -->

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

### Step 5: Interactive Claim Discussion

After presenting the result, engage the user before suggesting next steps. Reference the `interaction-patterns`, `claim-discussion`, and `counterexample-guide` skills.

**If FAIL → Gate checkpoint (Verification Claim Discussion)**:
1. State the violated property clearly: "Property X in isolate Y failed."
2. Show the relevant evidence (error line, counterexample trace if available).
3. Ask: "Is this property correct per the RFC? (yes → specification bug in IUT; no → model needs fixing; unsure → let's check the RFC together)"
4. Do NOT suggest next steps until the user has responded. Use the `counterexample-guide` skill to help interpret traces.

**If PASS → Inform-and-Continue**:
- State: "All properties verified successfully. Run `/nct-review` for deeper analysis or `/nct-compile` to build the test binary?"
- No gate needed — proceed with whatever the user says next.

---

**IMPORTANT**: Do NOT run `ivy_check` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`.

See the `workflow-reference` skill for verification debugging strategies.
