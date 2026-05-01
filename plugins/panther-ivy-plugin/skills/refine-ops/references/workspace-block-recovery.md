# Verify-ops — post-Edit workspace-block recovery

Recovery flow when `check-workspace-scope.py` PreToolUse hook blocks an `Edit` / `Write` on a `.ivy` file outside the active workspace during a Phase 7 fix application.

## Detection

After every `Write` / `Edit` on a `.ivy` file during Phase 7 (fix application), inspect the tool-result for a workspace-scope violation from the `check-workspace-scope.py` PreToolUse hook. The hook emits a "workspace scope violation" error (or an `additionalContext` marker naming the blocked file) when the target `.ivy` is outside the active workspace.

## Recovery flow

If the Edit was blocked:

1. Append a structured `progress` journal entry:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="progress",
     state='{"kind": "workspace_edit_blocked", "file": "<path>", "workspace_active": "<current>"}'
   )
   ```

2. Present `AskUserQuestion` with three options (per `.claude/rules/mcp-tool-reliability.md`'s escalation pattern):

   - **Switch workspace to the file's protocol** — run `/set-workspace <inferred-protocol>` (infer from the file's path relative to `protocol-testing/`), then retry the Edit.
   - **Clear workspace restrictions** — run `/clear-workspace`, then retry the Edit.
   - **Abandon this edit** — skip the edit; the fix loop continues with the change unapplied. Record a `decision` entry:
     ```
     decision{summary: "Edit skipped: workspace-blocked", context: "<file> outside <workspace>"}
     ```

## Platform limitation

If the harness does not surface workspace-scope-violation errors in the tool-result (platform limitation), this recovery path never fires — the Edit silently succeeds or silently fails at the filesystem layer. That case is a platform-level deficiency tracked as an upstream issue; the recovery pattern documented above remains correct for when the signal does reach user-space.
