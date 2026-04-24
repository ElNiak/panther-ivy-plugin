# Verify Workflow — Plan-Mode Preamble

Full detail of Phase 0 plan-mode handling for the verify workflow. Plan mode blocks `ivy_verify`, `ivy_compile`, and any tool that mutates state, so the normal verify cycle cannot proceed.

## Detection signals

Before running any verify-phase logic, inspect the session context. Any one signal is sufficient:

1. The literal phrase `Plan mode is active` in a system-reminder.
2. The edit-restriction phrase `You MUST NOT make any edits`.
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode system-reminder.

## 5-step plan-authoring procedure

If any indicator is present, switch to plan authoring instead of verify dispatch:

1. **Read-only context gathering only** — check the workflow journal for recent `error`, `gate_verdict`, and `decision` entries; skip any step that would mutate state.

2. **Situation briefing via `AskUserQuestion`** framed for plan-mode options:
   - "Draft a plan for the verify failure we hit"
   - "Draft a plan to restructure the verification approach"
   - "Clarify the verification scope before writing"
   - "Learn the Ivy verification model first"

3. **Help the user draft the plan** at the path named in the plan-mode system-reminder. If the plan covers a non-trivial implementation, invoke `Skill(skill="superpowers:writing-plans")`.

4. **Append `plan_approved` journal entry** before `ExitPlanMode`:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="plan_approved",
     payload={
       "workflow": "verify",
       "phase_before_plan": "<whatever phase the user was in>",
       "plan_file": "<absolute path>",
       "supersedes": ["<extracted from plan's ## Supersedes block if present>"]
     }
   )
   ```

5. **Call `ExitPlanMode`**.

## What NOT to do

Do NOT attempt to dispatch `ivy_verify`, `ivy_compile`, `ivy_iut_test`, or any state-mutating tool during plan mode — the call will be rejected and the session ends in an ambiguous state.

## Re-entry on next turn

Navigate's Phase 1.5 handles the re-entry on the next invocation after `ExitPlanMode`. The `plan_approved` journal entry is the hand-off signal; Phase 1.5 dispatches the G0 plan-gate and, on SOUND, emits `pending_dispatch(verify, phase_hint)` so navigate re-activates verify on the following turn.

See `skills/navigate/references/plan-mode-lifecycle.md` for the full Phase 1.5 procedure.
