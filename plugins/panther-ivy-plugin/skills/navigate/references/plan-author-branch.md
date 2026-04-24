# Navigate — Plan-Author Branch

Cold-path procedure extracted from `navigate/SKILL.md` so the hub skill
stays lean. Load this file when Phase 0 has detected plan mode and you need
the full 5-step plan-authoring procedure.

## When this branch runs

<branch condition="Phase 0 detected plan mode (any of the 3 detection signals in .claude/rules/plan-mode.md)" name="plan-author">

Plan mode blocks state-mutating actions, so the normal workflow dispatch
cannot run. This branch replaces Phase 2's dispatch.

</branch>

## 5-step procedure

<instructions>

1. **Silent context scan (read-only)** — Phase 1 Steps 1–3 and 2b only. Skip
   Step 4 (triage preflight) because triage may mutate state.
2. **Situation Briefing** via `AskUserQuestion`, framed for plan-mode
   options: "Write a plan for X" / "Audit existing plan" / "Clarify scope" /
   "Learn before planning".
3. **Draft the plan** at the path named in the plan-mode system-reminder.
   For non-trivial implementations, invoke
   `Skill(skill="superpowers:writing-plans")`. Present option-level
   decisions via `AskUserQuestion` throughout (per
   `feedback_askuserquestion_always`); implementation-plan tasks present
   2–3 options per modification task (per `feedback_plan_task_options`).
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

   The `supersedes` array is populated from a `## Supersedes` block in the
   plan file, if present.
5. **Call `ExitPlanMode`** to return control to the harness.

</instructions>

## Re-entry on the next turn

Navigate's Phase 1.5 handles re-entry. The `plan_approved` journal entry is
the hand-off signal; Phase 1.5 dispatches the G0 plan-gate and, on
<severity class="gate" value="SOUND"/>, emits
`pending_dispatch(<caller>, phase_hint)` so navigate re-activates the
caller workflow on the following turn.

Full Phase 1.5 procedure (G0 dispatch, asymmetric-vote aggregation,
`pending_dispatch` emission, UNSOUND/ABSTAIN handling, journal payload
shapes, `supersedes` extraction rule, fallback behavior, best-effort
caller inference): `references/plan-mode-lifecycle.md`.

<integration
  called-from="navigate/SKILL.md Phase 0 (plan-mode detection)"
  re-entry-via="navigate Phase 1.5 on the invocation after ExitPlanMode"
  related-rule=".claude/rules/plan-mode.md"/>
