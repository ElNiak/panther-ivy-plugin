# Verify Workflow — Background Verification Reference

Detailed procedure for running `ivy_verify` in a background subagent during the verify workflow, so productive work continues in the main conversation while long verifications run.

---

## When to Use

- The target file is large or verification historically takes >60s.
- The user has asked for parallel work, or there are independent tasks remaining (coverage checks, code review, diagnostics on other files).
- You are in a workflow phase where subsequent steps do not depend on the verification result.

Do NOT background when:

- The next step immediately depends on the result (e.g., Phase 6 diagnosis needs the failure output).
- The user explicitly wants to wait.

## How to Background

Spawn a background subagent with a self-contained prompt:

```
Agent(
  description: "Background ivy_verify",
  run_in_background: true,
  prompt: "Call the ivy_verify MCP tool with relative_path='<path>' in workspace '<protocol>'.
           Report the full result: pass/fail, property count, any counterexample traces, duration.
           If the tool errors or times out, report that too."
)
```

The subagent loads MCP servers independently and calls `ivy_verify`. A notification arrives when it completes.

## During the Wait

Continue with work that does not depend on the verification result:

- `ivy_coverage` or `ivy_diagnostics` on other files
- Reading and reviewing Ivy source for structural issues
- File edits, grep, git operations
- Other MCP tool calls (`ivy_model_info`, `ivy_analysis(mode="includes")`, `ivy_patterns`)

Avoid calling `ivy_verify` or `ivy_compile` in the main conversation while a background verification runs — the MCP semaphore limits concurrent tool execution.

## Picking Up the Result

When the background agent completes, read its result and integrate into the current workflow phase:

- **PASS** → Update workflow state, proceed to next phase (Phase 5 or completion).
- **FAIL** → Transition to Phase 6 (Diagnose) with the failure output.
- **ERROR/TIMEOUT** → Report to user, offer to retry synchronously.

The staleness rule still applies: if any `.ivy` file was edited after the background verification started, the result is stale and must be re-run.
