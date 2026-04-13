---
name: verify
description: "Test-compile-execute cycle with failure diagnosis. Use when the user wants to check, test, debug, or verify Ivy specifications."
---

## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
your active workflow overlay and phase modifier. Do not invent your own
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.

# Verify Workflow

Read `.panther-ivy/active-workflow` on every turn to determine your current phase. Update the phase field as you transition.

---

## Phase 1 — Preflight

### Step 1: Stack health check

Invoke the `triage` skill as a sub-workflow. Before invoking, write the active-workflow flag:

- `workflow = "triage"`
- `phase = "preflight"`
- `invocation_depth` = current depth + 1
- `caller = "verify"`

Invoke: `Skill(skill="triage")`

Triage runs Phase 1 only (because `invocation_depth > 0`). If the stack is healthy it returns silently. If something is broken, triage handles diagnosis and repair interactively before returning here.

After triage returns, restore the active-workflow flag:

- `workflow = "verify"`
- `phase = "preflight"`

### Step 2: Detect target protocol

Resolve the protocol in this order:

1. Check `IVY_WORKSPACE_ROOT` environment variable
2. Check the active workspace state via `ivy_workspace(action="get")`
3. Scan the current working directory for `protocol-testing/` subdirectories

If the protocol is still ambiguous, ask the user: "Which protocol are you working with?"

### Step 3: Update state

Update the active-workflow phase to `"preflight-done"` via `update_workflow_phase()`.

---

## Phase 2 — Test Selection

### Step 1: Scan existing tests

Look in `protocol-testing/{protocol}/{protocol}_tests/` for files matching `*_test*.ivy`. Group them by subdirectory:

- `server_tests/` — tests targeting server IUTs (Ivy acts as client)
- `client_tests/` — tests targeting client IUTs (Ivy acts as server)
- `mim_tests/` — man-in-the-middle attack tests

### Step 2: Present options

Offer the user three choices:

1. **Run ALL existing tests** for the target protocol
2. **Pick specific test(s)** from the list found in Step 1
3. **Design a new test inline** — this pulls supplementary knowledge for test authoring

If the user picks option 3, invoke the `ivy-writing-guide` skill and the `specification-patterns` skill to load authoring guidance. Guide the user through creating the test spec, then continue to Phase 3.

### Gate checkpoint

Wait for the user to confirm which test(s) to run or create. Do not proceed until you have explicit confirmation.

### Step 3: Update state

Update phase to `"test-selected"` via `update_workflow_phase()`.

---

## Phase 3 — Compile

For each selected test file, call:

```
ivy_compile(relative_path=<test_file>, target="test")
```

### On SUCCESS

Move to Phase 4. Update phase to `"compiled"` via `update_workflow_phase()`.

### On compile ERROR

1. Dispatch the `spec-analyst` agent with the full error output for diagnosis.
2. The spec-analyst returns a diagnosis and a fix suggestion.
3. Present the diagnosis and suggested fix to the user.
4. If the user agrees to apply the fix, apply it, then loop back to Phase 3 (recompile).
5. If the user declines, ask whether they want to fix it themselves or abandon.

---

## Phase 4 — Execute

Run the compiled test:

```
ivy_verify(relative_path=<test_file>)
```

### On PASS

1. Report: "Verification passed for `<test_file>`."
2. Offer follow-ups: "Run another test? Check coverage? Review model quality?"
3. If the user picks coverage or review, dispatch to the `review` workflow as a sub-workflow:
   - Set `invocation_depth` += 1, `caller = "verify"` on the active-workflow flag
   - Invoke: `Skill(skill="review")`
4. Update phase to `"pass"`, then proceed to completion.

### On FAIL

Move to Phase 6. Update phase to `"executed"` via `update_workflow_phase()`.

---

## Phase 5 — IUT Testing (optional)

Only entered after Phase 4 succeeds (formal verification passes). Skipped when `invocation_depth > 0` (verify called as sub-workflow from build).

### Step 1: Offer IUT testing

Present the user with the option:

> "Formal verification passed. Want to run this test against a real implementation?"

If the user declines, proceed directly to completion (On Completion section).

### Step 2: Select IUT

Scan `panther/plugins/services/iut/{protocol}/` for available IUT plugin directories. Present as numbered options:

```
Available IUTs for {protocol}:
1. frr_bgp
2. (other IUT if multiple exist)
```

If only one IUT exists, suggest it directly and ask for confirmation.

### Step 3: Execute

Call the MCP tool:

```
ivy_iut_test(protocol=<detected>, test_name=<from Phase 2>, iut_name=<selected>)
```

### On PASS

1. Report: "IUT test passed. `<test_name>` succeeded against `<iut_name>` in {duration_seconds}s."
2. Show `output_dir` for reference.
3. Offer follow-ups: "Run another test? Check coverage? Review model quality?"
4. Update phase to `"iut-pass"`, then proceed to completion.

### On FAIL

1. Present the `iut_logs` content from the tool result.
2. Present key details from `experiment_summary` (test status, error message if any).
3. Show `output_dir`: "Full experiment output at `{output_dir}` — use Read to inspect further."
4. Offer: "Want me to investigate the failure? Or fix it yourself?"
5. If user wants investigation, move to Phase 6 (Diagnose) with the IUT failure context.
6. Update phase to `"iut-fail"`.

### On ERROR or TIMEOUT

1. Present the error details from `test_stderr`.
2. Suggest: "Check Docker status (`docker ps`), verify IUT plugin configuration, and ensure the test binary compiled successfully."
3. Update phase to `"iut-error"`.

### Step 4: Update state

Update active-workflow phase via `update_workflow_phase()`.

---

## Phase 6 — Diagnose

### Step 1: Load failure interpretation guidance

Invoke the `counterexample-guide` skill to load trace interpretation guidance.

### Step 2: Dispatch spec-analyst

Dispatch the `spec-analyst` agent with the full failure trace output.

### Step 3: Classify the failure

Classify into one of three categories:

- **Invariant violation** — a property that should hold does not. The counterexample trace shows a reachable state where an invariant or `require` is falsified.
- **Type error** — type mismatch, missing type interpretation, or unresolved type in the model.
- **Structural issue** — include path problems, missing modules, circular dependencies, unresolved symbols.

On structural issues, also dispatch the `model-reviewer` agent for a deeper audit of the model's include graph and layer structure.

### Step 4: Present diagnosis

Report to the user with the failure classification and the spec-analyst's diagnosis.

### Gate checkpoint

Ask the user: "Fix it yourself, or want me to attempt the fix?"

Wait for explicit confirmation before proceeding.

### Step 5: Update state

Update phase to `"diagnosed"` via `update_workflow_phase()`.

---

## Phase 7 — Fix (optional)

Only entered if the user accepts the auto-fix offer from Phase 6.

### Step 1: Apply the fix

Apply the fix suggested by the spec-analyst. If editing `.ivy` files, invoke the `ivy-writing-guide` skill to load language reference guidance before making changes.

### Step 2: Re-verify

Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) → Phase 4 (execute) → Phase 6 (diagnose) → Phase 7 (fix) → Phase 3 again.

This loop continues until verification passes or the user decides to stop.

### On user stopping

Update phase to `"stopped"` and proceed to completion.

---

## On Completion

- If `invocation_depth > 0`: Decrement depth. Restore `caller` as the active workflow in the active-workflow file. The caller resumes.
- If `invocation_depth == 0`: Clear the active-workflow flag via `clear_active_workflow()`. Navigate re-activates on the next user turn.

---

## Integration

- **Called by:** `navigate` (dispatch), `build` (post-build verification), user directly ("verify this", "run tests")
- **Calls:** `triage` (preflight), `spec-analyst` agent (diagnosis), `model-reviewer` agent (structural audit), `review` workflow (follow-up coverage)
- **Knowledge skills loaded:** `counterexample-guide` (Phase 6), `ivy-writing-guide` (Phase 2 option 3, Phase 7), `specification-patterns` (Phase 2 option 3)
- **MCP tools used:** `ivy_compile`, `ivy_verify`, `ivy_workspace`, `ivy_iut_test`
- **State files:** `.panther-ivy/active-workflow`
