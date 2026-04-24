---
paths: ["**/skills/*/SKILL.md", "**/*.ivy", "**/*.spec"]
---

# Plan mode handling

When the Claude Code harness activates plan mode, state-mutating tools are blocked and the active workflow must switch to plan authoring. This rule codifies the shared detection-and-authoring protocol so each workflow skill (`navigate`, `build`, `verify`, `review`) only needs to express its own caller-specific option framings.

## Detection signals

Any single indicator is sufficient. Inspect system-reminder messages and `additionalContext` blocks accumulated since session start:

1. The literal phrase `Plan mode is active` in a system-reminder.
2. The edit-restriction phrase `You MUST NOT make any edits`.
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode system-reminder (e.g. `"No plan file exists yet. You should create your plan at /Users/<user>/.claude/plans/<name>.md"`).

The three exist because plan-mode activation surfaces at different places depending on whether it was set via CLI flag, keybinding, or `EnterPlanMode` mid-session.

## 5-step plan-authoring procedure

If any indicator is present, switch to plan authoring instead of the normal workflow cycle:

1. **Read-only context gathering.** Check the workflow journal for recent `error`, `gate_verdict`, and `decision` entries; inspect `build-state.yaml` if present; skip any step that would mutate state or dispatch a state-mutating MCP tool.

2. **Situation briefing via `AskUserQuestion`**, framed for plan-mode options. The option set is workflow-specific — each calling skill's Phase 0 block provides its own concrete framings.

3. **Help the user draft the plan** at the path named in the plan-mode system-reminder. If the plan covers a non-trivial implementation, invoke `Skill(skill="superpowers:writing-plans")`. Present option-level decisions via `AskUserQuestion` throughout (per `feedback_askuserquestion_always`); implementation-plan tasks present 2–3 options per modification task (per `feedback_plan_task_options`).

4. **Append a `plan_approved` journal entry** before `ExitPlanMode`:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="plan_approved",
     payload={
       "workflow": "<caller workflow, e.g. build, verify, review>",
       "phase_before_plan": "<phase name the caller was in>",
       "plan_file": "<absolute path to the plan file>",
       "supersedes": ["<optional list of build-state decisions the plan reverses>"]
     }
   )
   ```
   The `supersedes` array is populated from a `## Supersedes` block in the plan file, if present.

5. **Call `ExitPlanMode`** to return control to the harness.

## Plan-mode tool surface

During plan mode, restrict yourself to read-only MCP tools and plan-file edits. State-mutating tools (`ivy_compile`, `ivy_verify`, `ivy_iut_test`, `ivy_coverage`, `ivy_quality`, `ivy_extract_requirements`, `Write`/`Edit` on `.ivy` files) are rejected by the harness and leave the session in an ambiguous state. The plan file named in the plan-mode system-reminder is the single exception — edit it freely.

## Re-entry on the next turn

Navigate's Phase 1.5 handles re-entry on the invocation after `ExitPlanMode`. The `plan_approved` journal entry is the hand-off signal; Phase 1.5 dispatches the G0 plan-gate and, on SOUND, emits `pending_dispatch(<caller>, phase_hint)` so navigate re-activates the caller workflow on the following turn.

Full Phase 1.5 procedure (G0 dispatch, asymmetric-vote aggregation, `pending_dispatch` emission, UNSOUND/ABSTAIN handling) lives in `skills/navigate/references/plan-mode-lifecycle.md`.
