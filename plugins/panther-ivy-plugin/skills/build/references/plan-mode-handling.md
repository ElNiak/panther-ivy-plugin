# Build — Plan-mode Handling

Cold-path guidance extracted from `build/SKILL.md` so the session-loaded
skill stays lean. Load this file when the session is in plan mode and the
build workflow needs to switch to plan-authoring behavior instead of the
normal build cycle.

## Phase 0 — Plan-mode preamble

Before running any build-phase logic, inspect the session context for plan-mode indicators. Plan mode blocks `ivy_compile`, `Write`/`Edit` on `.ivy` files, and any tool that mutates state, so the normal build cycle cannot proceed.

Detection signals (any one is sufficient):

1. The literal phrase `Plan mode is active` in a system-reminder.
2. The edit-restriction phrase `You MUST NOT make any edits`.
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode system-reminder.

If any indicator is present, switch to plan authoring instead of build dispatch:

1. Run read-only context gathering only: check the workflow journal for recent `error`, `gate_verdict`, and `decision` entries; inspect `build-state.yaml` if present; skip any step that would mutate state or scaffold new `.ivy` files.
2. Present a situation briefing via `AskUserQuestion` framed for plan-mode options — "draft a plan for the new layer we need", "draft a plan to restructure the blueprint", "clarify the modeling scope before writing", "learn the 14-layer template first".
3. Help the user draft the plan at the path named in the plan-mode system-reminder. If the plan covers a non-trivial implementation, invoke `Skill(skill="superpowers:writing-plans")`.
4. Before `ExitPlanMode`, append a `plan_approved` journal entry with `workflow: "build"`, `phase_before_plan: <whatever phase the user was in>`, `plan_file`, and `supersedes` (extracted from the plan's `## Supersedes` block if present).
5. Call `ExitPlanMode`.

Do NOT attempt to dispatch `ivy_compile`, `ivy_verify`, `Write`, `Edit`, or any state-mutating tool during plan mode — the call will be rejected and the session ends in an ambiguous state. Navigate's Phase 1.5 handles the re-entry on the next invocation after `ExitPlanMode`.
