# Navigate — Plan-Mode Lifecycle Reference

Full detail for the three plan-mode-related sections of the navigate workflow: the
Phase 0 detection protocol, the Phase 1.5 post-plan-approval handoff, and the
Plan-Author Branch that runs in place of Phase 2's dispatch while plan mode is active.

The SKILL.md body keeps the load-bearing routing rule inline and points at this
reference for every detail below.

---

## Phase 0 — Plan-mode detection (full detail)

Before the silent context scan, inspect the active session context for plan-mode
indicators. Plan mode is a Claude Code harness feature that forbids non-plan edits;
if active, navigate must route to the Plan-Author Branch rather than dispatching a
workflow that would mutate state.

### Detection signals

<plan_mode_detection_signals>
Look for any of these in the session's system-reminder messages and
`additionalContext` blocks accumulated since session start:

1. The literal phrase `Plan mode is active`.
2. The edit-restriction phrase `You MUST NOT make any edits` (plan mode's
   enforcement text).
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode
   system-reminder (e.g., `No plan file exists yet. You should create your plan at
   /Users/<user>/.claude/plans/<name>.md`).

Any single indicator is sufficient. The three exist because Claude Code's plan-mode
activation surfaces at different places depending on whether plan mode was set via
CLI flag, keybinding, or `EnterPlanMode` mid-session.
</plan_mode_detection_signals>

This is the canonical `<plan_mode_detection_signals>` block. Other workflow skills (`build`, `verify`, `review`) point here rather than duplicating the list.

### Routing rule

- **If any indicator is present**: set mode = `plan-author`. Skip Phase 1's Step 4
  (triage preflight) because it mutates state. Run the read-only parts of Phase 1
  (the silent context scan is safe in plan mode), then route to the **Plan-Author
  Branch** (further down this reference) instead of Phase 2's dispatch.
- **If no indicator is present**: proceed to Phase 1 normally.

### Journal note

After Phase 0 routes to Plan-Author (or falls through to Phase 1), append a
`context_switch` journal entry recording the detection outcome:

```
ivy_workflow_state(
  action="append_journal",
  protocol="<protocol>",
  event_type="context_switch",
  payload={"detection": "plan_mode_active" | "plan_mode_inactive",
           "mode": "plan-author" | "normal"}
)
```

This is advisory — if the MCP tool is unavailable (e.g., during plugin development
sessions), skip the journal write and continue. The detection outcome is also
captured downstream by the Plan-Author Branch's `plan_approved` entry.

---

## Phase 1.5 — Post-plan-approval handoff (full procedure)

Fires only on the turn after `ExitPlanMode`. Phase 0 and Phase 1.5 are mutually
exclusive — if Phase 0 routed to the Plan-Author Branch (plan mode is still active),
Phase 1.5 does NOT fire. Phase 1.5 fires when plan mode is NO LONGER active AND the
workflow journal shows a recent `plan_approved` entry that has not yet been paired
with a `workflow_resumed` entry.

### Trigger condition

After Phase 1's context scan completes, inspect the last few journal entries:

```
ivy_workflow_state(action="get_journal", protocol="<protocol>", last_n=10)
```

Phase 1.5 runs if BOTH:

1. Phase 0's detection did NOT fire (plan mode is not active on this turn).
2. The most recent `plan_approved` entry has no subsequent `workflow_resumed` entry.

Otherwise, proceed to Phase 2.

### Step 1 — Load the plan file

Read the path from the `plan_approved` entry's `plan_file` field. Use `Read` on that
path. If the file is missing (user deleted it after approval), log an `error`
journal entry and halt with a message to the user asking how to proceed.

### Step 2 — Extract committed decisions

Scan the plan file for these structured markers:

- `## Supersedes` block listing prior `build-state.yaml` decisions the plan reverses.
- `Committed:` / `Committed design:` lines naming load-bearing design choices.
- `Revises:` lines naming prior `gate_verdict` entries the plan invalidates.

Extraction is best-effort — plans authored without these markers still proceed, but
the G0 critic will have less structured context to audit against. If the plan-author
convention evolves (e.g., a YAML front-matter block), this step extends.

### Step 3 — Dispatch G0 plan-gate

Load `reflection-patterns` and dispatch the G0 variant:

```
Skill(skill="panther-ivy-plugin:cross-cutting-reflection-patterns")
```

Then, following the discipline contracts from the loaded `reflection-patterns`
skill (its `references/gates.md` for contract semantics, its
`references/critic_prompts/g0_plan.md` for the verbatim G0 critic template), spawn
3 Opus critics in parallel (single message, three `Agent` tool calls). Provide each
critic with:

- Absolute path to the plan file.
- The `plan_approved` journal entry contents.
- Current `build-state.yaml` contents.
- Superseded `decision` and `gate_verdict` journal entries (if any).
- The methodology overlay (`NCT` / `NACT` / `NSCT`) from
  `build-state.yaml:methodology`.

Each critic returns `SOUND`, `UNSOUND(#NN, …)`, or `ABSTAIN`.

### Step 4 — Record the verdict

Aggregate the three critics per the asymmetric-vote rule (Opus × 3,
confirmer-threshold 2, refute-threshold 1) and write the outcome:

```
ivy_workflow_state(
  action="append_journal",
  protocol="<protocol>",
  event_type="gate_verdict",
  payload={
    "gate": "g0",
    "verdict": "SOUND" | "UNSOUND" | "ABSTAIN",
    "vote": {"sound": int, "unsound": int, "abstain": int},
    "patterns": [...],
    "cycle": <1-3>,
    "tier": "opus",
    "duration_s": <elapsed>
  }
)
```

### Step 5 — SOUND: emit pending_dispatch to re-activate caller workflow

If `verdict == SOUND`:

1. Update `build-state.yaml`'s `decisions:` block by merging the plan's committed
   decisions, marking any superseded entries with `status: superseded_by:
   <plan_file>`.
2. Emit a `pending_dispatch` naming the caller workflow (read from the
   `plan_approved` entry) with the next phase as `phase_hint`. For a build that
   was in `blueprint-done-revise-N`, the next phase after a SOUND G0 is `modeling`:

   ```
   append_pending_dispatch(
     protocol="<protocol>",
     target_workflow="<caller>",
     phase_hint="<next phase>",
     reason="G0 SOUND on cycle <N>"
   )
   ```

3. Clear navigate's active-workflow flag via
   `ivy_workflow_state(action="clear", protocol="<protocol>")` and end the turn.
   Navigate's Phase 1 Step 2c on the next user turn (or same turn if the harness
   routes the `pending_dispatch` back to navigate in-line) consumes the entry and
   dispatches `<caller>` with the `phase_hint`, writing the paired
   `workflow_resumed` marker as part of Step 2c's idempotency protocol.

Navigate does NOT call `Skill(skill="panther-ivy-plugin:<caller>")` directly here —
the hand-off rides on `pending_dispatch` so the journal carries the full causal
chain (`plan_approved` → `gate_verdict{SOUND}` → `pending_dispatch` →
`workflow_resumed`).

### Step 6 — UNSOUND: surface and halt

If `verdict == UNSOUND`:

1. Present the dissenter reasons to the user via `AskUserQuestion` (per
   `feedback_askuserquestion_always`). Include the cited pattern IDs, file:line
   locators, and each critic's justification.
2. Offer three follow-up options:
   - **Revise the plan** — re-enter plan mode to fix the flagged issues. Phase 1.5
     re-fires on the next approval (cycle counter increments, budget is 3).
   - **Overrule G0** — user authority accepts the verdict against the critics.
     Record a `decision` journal entry with `override_reason: <user-provided>`
     before re-activating the workflow.
   - **Defer** — pause without re-activation; the `plan_approved` entry remains
     open until the next Phase 1.5 run.
3. Do NOT re-activate the workflow on UNSOUND without explicit user input.

If the cycle count reaches 3 and the verdict is still UNSOUND, escalate: halt with
a summary of all three cycles' dissenter reasons and wait for user direction. Do
not auto-overrule.

### Step 7 — ABSTAIN: insufficient evidence

If `verdict == ABSTAIN`:

1. Present the abstain reasons to the user (usually "critic could not decide
   without X").
2. Offer to gather the missing evidence (RFC text fetch, additional file reads,
   wider journal scan) and re-run G0.

ABSTAIN does not consume a cycle from the 3-cycle budget; only `UNSOUND` does.

---

## Plan-Author Branch (full 5-step procedure)

This branch replaces Phase 2's dispatch. Plan mode blocks state-mutating actions,
so the normal workflow-dispatch path cannot run. The Plan-Author Branch gathers
context, helps the user draft the plan, records an auditable handoff, and then
ExitPlanMode returns control to the harness.

### Step 1 — Silent context scan (safe in plan mode)

Run Phase 1's Steps 1–3 (locate protocol, check active build, check recent `.ivy`
changes) and Step 2b (check workflow journal). Skip Step 4 (triage preflight)
because triage may mutate state. Gather the same context that normal navigate
would — the information is still useful even though dispatch won't happen.

### Step 2 — Situation Briefing framed for plan-mode options

Load `reflection-patterns` skill and apply Pattern C (Situation Briefing) with
options framed for plan authoring rather than workflow dispatch:

- "Write a plan for X" — where X is inferred from the user's opening question and
  the context scan.
- "Audit an existing plan" — if the user references an existing plan file.
- "Clarify scope before writing" — when the user's intent is ambiguous enough that
  drafting would be premature.
- "Learn before planning" — if the context suggests the user should load a
  methodology or syntax reference first.

### Step 3 — Draft the plan

When the user is ready to draft, help them produce the plan file at the path named
in the plan-mode system-reminder (e.g., `/Users/<user>/.claude/plans/<name>.md`).
If the plan involves a non-trivial implementation, invoke
`Skill(skill="superpowers:writing-plans")` to apply that skill's structure. Do NOT
attempt to dispatch `build`, `verify`, or `review` — they would fail under plan
mode's edit restrictions.

Throughout drafting, present option-level decisions via `AskUserQuestion` (not
inline prose) per the `feedback_askuserquestion_always` convention. Implementation-
plan tasks should present 2–3 options per modification task per
`feedback_plan_task_options`.

### Step 4 — Append `plan_approved` journal entry

Before the user calls `ExitPlanMode`, append the handoff record that Phase 1.5 will
consume on the next invocation:

```
ivy_workflow_state(
  action="append_journal",
  protocol="<protocol>",
  event_type="plan_approved",
  payload={
    "workflow": "<caller workflow, e.g. build or verify>",
    "phase_before_plan": "<phase name the caller was in>",
    "plan_file": "<absolute path to the plan file>",
    "supersedes": ["<optional list of build-state decisions the plan reverses>"]
  }
)
```

The `caller` field is best-effort: if `active-workflow` names a paused workflow,
use that; otherwise infer from the user's opening intent. The `supersedes` array is
populated from a `## Supersedes` block in the plan file, if present.

### Step 5 — ExitPlanMode

Call `ExitPlanMode` to return control to the harness. Navigate's Phase 1.5 fires on
the next user turn to dispatch G0 and re-activate the caller workflow.
