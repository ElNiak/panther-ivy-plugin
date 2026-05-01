# Scaffold Workflow — Background Compilation Reference

Detailed procedure for running `ivy_compile` in a background subagent during Phase 3 of the scaffold workflow, so productive work continues in the main conversation while long compilations run.

---

## When to Use

- The model is large and compilation historically takes >60s.
- There are independent tasks remaining (writing the next layer's scaffold, reviewing existing layers, running diagnostics on other files).
- The current layer's implementation is complete and the compile confirmation is pending.

Do NOT background when: the next step requires the compile result (e.g., diagnosing a compile error inline), or when writing a single small layer where the compile is fast.

## How to Background

Spawn a background subagent with a self-contained prompt:

```
Agent(
  description: "Background ivy_compile",
  run_in_background: true,
  prompt: "Call the ivy_compile MCP tool with relative_path='<path>' and target='test' in workspace '<protocol>'.
           Report the full result: success/failure, any error messages with line numbers, duration.
           If the tool errors or times out, report that too."
)
```

The subagent loads MCP servers independently and calls `ivy_compile`. A notification arrives when it completes.

## During the Wait

Continue with work that does not depend on the compilation result:

- Scaffolding the next layer (if dependency order allows)
- Reviewing or editing other existing layers
- Running `ivy_diagnostics` or `ivy_coverage` on previously compiled files
- Reading RFC sections for upcoming layers

Avoid calling `ivy_verify` or `ivy_compile` in the main conversation while a background compilation runs — the MCP semaphore limits concurrent tool execution.

## Picking Up the Result

When the background agent completes, read its result and integrate into the current workflow phase:

- **SUCCESS**: Update `scaffold-state.yaml` layer status, proceed to next layer or Phase 4.
- **FAILURE**: Dispatch `spec-analyst` with the error output, fix inline, recompile (synchronously, since the feedback loop is needed).
- **ERROR/TIMEOUT**: Report to user, offer to retry synchronously.

The staleness rule still applies: if the `.ivy` file was edited after the background compilation started, the result is stale and must be re-run.
