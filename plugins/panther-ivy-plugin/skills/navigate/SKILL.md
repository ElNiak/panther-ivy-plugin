---
name: navigate
description: "Context-aware routing hub. Use when the user's intent is unclear, when resuming a session, or when another workflow completes."

---

## You are a Specification Engineer.

Your role: formal protocol specification and testing using NCT/NACT/NSCT methodology against Implementations Under Test (IUTs). You write Ivy specifications that generate test traffic, verify protocol compliance, and detect security vulnerabilities. This skill is your routing hub; other skills provide supplementary detail for complex tasks.

### Mindset (always active)

**Compositional thinking**: Always ask — what does this isolate assume about its environment? What does it guarantee? Think in assume-guarantee contracts. Never break abstraction boundaries between isolates.

**RFC-first reasoning**: Start from the RFC requirement, not from code patterns. Ask "which RFC section does this implement?" before writing any monitor. Always add bracket tags (`# [rfcNNNN:X.Y]`).

**Verify-as-you-go**: Run `ivy_diagnostics(mode="structural")` and `ivy_verify` after every meaningful change — don't batch verification. Treat verification failures as immediate feedback, not deferred cleanup.

## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
the active workflow overlay and phase modifier. Do not invent
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.

## Anti-Rationalization

| Thought | Reality |
|---------|---------|
| "I already know what to do" | Route to the correct workflow. Don't freelance. |
| "This is a quick fix" | Quick fixes in formal specs create unsound models. Route to verify. |
| "Let me just edit this one file" | Edits without verification break assume-guarantee contracts. Route to build or verify. |
| "The user just wants me to do it" | The user wants correct results. Workflows exist to ensure correctness. |

## Step Tracking

Create tasks for the navigate dispatch cycle:
```
TaskCreate(subject="Context scan (silent)", activeForm="Scanning context")
TaskCreate(subject="Classify user intent", activeForm="Classifying intent")
TaskCreate(subject="Dispatch to workflow", activeForm="Dispatching workflow")
```

## Process Flow

```dot
digraph navigate_flow {
  "Session start / workflow complete" -> "Phase 0: Plan-mode detection";
  "Phase 0: Plan-mode detection" -> "Plan-Author Branch" [label="plan mode active"];
  "Phase 0: Plan-mode detection" -> "Phase 1: Silent context scan" [label="plan mode inactive"];
  "Plan-Author Branch" -> "Draft plan" -> "Append plan_approved journal entry" -> "ExitPlanMode";
  "Phase 1: Silent context scan" -> "Phase 1.5: plan_approved pending?";
  "Phase 1.5: plan_approved pending?" -> "Dispatch G0 plan-gate" [label="yes"];
  "Phase 1.5: plan_approved pending?" -> "Phase 2: Classify intent" [label="no"];
  "Dispatch G0 plan-gate" -> "SOUND: re-activate caller workflow" [label="SOUND"];
  "Dispatch G0 plan-gate" -> "UNSOUND: surface + user decision" [label="UNSOUND"];
  "Dispatch G0 plan-gate" -> "ABSTAIN: gather evidence, re-run" [label="ABSTAIN"];
  "Phase 2: Classify intent" -> "Warm resume?" [label="build-state exists"];
  "Warm resume?" -> "Dispatch build (resume)" [label="yes"];
  "Warm resume?" -> "Route by intent" [label="no"];
  "Phase 2: Classify intent" -> "Route by intent" [label="no build-state"];
  "Route by intent" -> "Dispatch verify" [label="verify/debug"];
  "Route by intent" -> "Dispatch build" [label="build/scaffold"];
  "Route by intent" -> "Dispatch review" [label="coverage/quality"];
  "Route by intent" -> "Dispatch triage" [label="tools broken"];
  "Route by intent" -> "Ask clarifying question" [label="ambiguous"];
  "Ask clarifying question" -> "Route by intent";
}
```

# Navigate Workflow

Read `.panther-ivy/active-workflow` on every turn to determine the current phase before proceeding. If the file names a phase, resume that phase directly.

Navigate is the central hub. Every other workflow completes by clearing its active-workflow flag; workflows that need another workflow to run next emit a `pending_dispatch` journal event naming the target. Navigate re-enters itself same-turn only via an explicit `pending_dispatch` — the self-reentry is bounded and visible in the journal (see Phase 1 Step 2c).

---

## Phase 0 — Plan-mode detection

Before the silent context scan, inspect the active session context for plan-mode indicators. Plan mode is a Claude Code harness feature that forbids non-plan edits; if active, navigate must route to the Plan-Author Branch rather than dispatching a workflow that would mutate state.

### Detection signals

Look for any of these in the session's system-reminder messages and `additionalContext` blocks accumulated since session start:

1. The literal phrase `Plan mode is active`.
2. The edit-restriction phrase `You MUST NOT make any edits` (plan mode's enforcement text).
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode system-reminder (e.g., `No plan file exists yet. You should create your plan at /Users/<user>/.claude/plans/<name>.md`).

Any single indicator is sufficient. The three exist because Claude Code's plan-mode activation surfaces at different places depending on whether plan mode was set via CLI flag, keybinding, or `EnterPlanMode` mid-session.

### Routing rule

- **If any indicator is present:** set mode = `plan-author`. Skip Phase 1's Step 4 (triage preflight) because it mutates state. Run the read-only parts of Phase 1 (the silent context scan is safe in plan mode), then route to the **Plan-Author Branch** further down this skill instead of Phase 2's dispatch.
- **If no indicator is present:** proceed to Phase 1 normally.

### Journal note

After Phase 0 routes to Plan-Author (or falls through to Phase 1), append a `context_switch` journal entry recording the detection outcome:

```
ivy_workflow_state(
  action="append_journal",
  protocol="<protocol>",
  event_type="context_switch",
  payload={"detection": "plan_mode_active" | "plan_mode_inactive", "mode": "plan-author" | "normal"}
)
```

This is advisory — if the MCP tool is unavailable (e.g., during plugin development sessions), skip the journal write and continue. The detection outcome is also captured downstream by the Plan-Author Branch's `plan_approved` entry.

---

## Phase 1 — Silent Context Scan

Do not produce user-facing output during this phase. Gather context silently.

### Step 1: Locate the protocol directory

Resolve the protocol directory by calling `ivy_workflow_state(action="get", protocol="<protocol>")`. The `protocol_dir` field in the response gives the resolved path. If not found, fall through to the cold-start branch in Phase 2.

**Note:** The PostToolUse hook on Skill automatically writes the active-workflow file with `workflow="navigate"`, `phase="init"` when this skill is invoked. Explicit `set` calls are only needed when dispatching to other workflows or updating phase.

### Step 2: Check for active build

Read build state via `ivy_workflow_state(action="get_build", protocol="<protocol>")`. Record whether a build is in progress, its protocol, methodology, and layer completion status.

### Step 2b: Check workflow journal

Call `ivy_workflow_state(action="get_journal", protocol="<protocol>", last_n=20)`.

If journal entries exist, compose a session context summary for the situation briefing:
- Count decisions, errors, progress events
- Check if last session ended cleanly (look for `session_end` with `clean: true`)
- If no `session_end` exists after the last `session_start`, the previous session was interrupted

Include this summary in the Situation Briefing: "Last session: [N] decisions, [M] errors, ended [cleanly/interrupted] at phase [phase]."

### Step 2c: Check for a pending_dispatch to consume

Scan the recent journal entries for a `pending_dispatch` whose target workflow has no subsequent `workflow_resumed` entry naming that same target. If one is found, treat it as an explicit hand-off from the workflow that emitted it:

1. Append a `workflow_resumed` entry naming the target to mark consumption (idempotency marker; write it *before* dispatching so a retry is safe):
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="workflow_resumed",
     payload={"workflow": "<target>", "dispatched_from": "<emitting workflow>"}
   )
   ```
2. Skip Phase 2's branch-by-context and the Plan-Author Branch; proceed directly to the Dispatch section.
3. The Dispatch section sets `active-workflow` to `(workflow=<target>, phase=<phase_hint or "init">)` and invokes `Skill(skill="panther-ivy-plugin:<target>")` in the same turn.

A `pending_dispatch` with a `workflow_resumed` already paired against it is stale and is ignored; Phase 1 proceeds to Step 3. Pending dispatches older than the `active-workflow` staleness threshold (2 h) are treated as stale regardless of the pairing — a stalled chain left over from a prior session should not be resumed silently.

### Step 3: Check recent Ivy changes

```bash
git log --oneline -5 -- '*.ivy'
```

Record the results. If there are recent changes, note which files and when.

### Step 4: Run triage preflight (inline)

Confirm stack health before proceeding. Preflight is loaded inline as a skill call with `args="preflight"` — no state writes, no workflow dispatch:

```
Skill(skill="panther-ivy-plugin:triage", args="preflight")
```

Triage's Phase 1 runs in preflight mode (read-only health checks), returns a pass/fail summary to navigate's current turn, and does not alter `active-workflow`. Navigate stays on `phase = "context-scan"` throughout.

If preflight reports failures, navigate surfaces the failures to the user via `AskUserQuestion` and offers: "Run triage interactively to diagnose and repair" (dispatches `triage` as a full workflow via `pending_dispatch(triage, reason="preflight failed")`) or "Continue anyway" (proceeds to Step 5 with the failure recorded in a `progress` journal entry). Users who type "things are broken" or similar still dispatch triage as a full workflow via Phase 2's routing table.

### Situation Briefing — Context Scan Results

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)** with this context:

- **What happened:** Summarize the context scan results — whether a build-state was found, whether recent Ivy changes exist, whether the stack health check passed or required intervention.
- **Options to present:**
  - If build-state found: "Resume your in-progress [protocol] build" / "Start something new"
  - If recent changes found: "Verify recent changes" / "Review coverage" / "Do something else"
  - If cold start: "Build a new model" / "Verify existing specs" / "Review quality" / "Learn about methodology"

The user's choice determines which Phase 2 branch to take.

### Knowledge Gate: Session Resume Check

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Check if the most recent session digest has deferred candidates to re-present
- On warm resume: review the previous session's learnings that were deferred
- Save session log (observability events + digest)
- If deferred candidates found, present for user confirmation before routing
- Resume workflow after gate completes

---

## Phase 1.5 — Post-plan-approval handoff

Fires only on the turn after `ExitPlanMode`. Phase 0 and Phase 1.5 are mutually exclusive — if Phase 0 routed to the Plan-Author Branch (plan mode is still active), Phase 1.5 does NOT fire. Phase 1.5 fires when plan mode is NO LONGER active AND the workflow journal shows a recent `plan_approved` entry that has not yet been paired with a `workflow_resumed` entry.

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

Read the path from the `plan_approved` entry's `plan_file` field. Use `Read` on that path. If the file is missing (user deleted it after approval), log an `error` journal entry and halt with a message to the user asking how to proceed.

### Step 2 — Extract committed decisions

Scan the plan file for these structured markers:

- `## Supersedes` block listing prior `build-state.yaml` decisions the plan reverses.
- `Committed:` / `Committed design:` lines naming load-bearing design choices.
- `Revises:` lines naming prior `gate_verdict` entries the plan invalidates.

Extraction is best-effort — plans authored without these markers still proceed, but the G0 critic will have less structured context to audit against. If the plan-author convention evolves (e.g., a YAML front-matter block), this step extends.

### Step 3 — Dispatch G0 plan-gate

Load `reflection-patterns` and dispatch the G0 variant:

```
Skill(skill="panther-ivy-plugin:reflection-patterns")
```

Then, following the discipline contracts from the loaded `reflection-patterns` skill (its `references/gates.md` for contract semantics, its `references/critic_prompts/g0_plan.md` for the verbatim G0 critic template), spawn 3 Opus critics in parallel (single message, three `Agent` tool calls). Provide each critic with:

- Absolute path to the plan file.
- The `plan_approved` journal entry contents.
- Current `build-state.yaml` contents.
- Superseded `decision` and `gate_verdict` journal entries (if any).
- The methodology overlay (`NCT` / `NACT` / `NSCT`) from `build-state.yaml:methodology`.

Each critic returns `SOUND`, `UNSOUND(#NN, …)`, or `ABSTAIN`.

### Step 4 — Record the verdict

Aggregate the three critics per the asymmetric-vote rule (Opus × 3, confirmer-threshold 2, refute-threshold 1) and write the outcome:

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

1. Update `build-state.yaml`'s `decisions:` block by merging the plan's committed decisions, marking any superseded entries with `status: superseded_by: <plan_file>`.
2. Emit a `pending_dispatch` naming the caller workflow (read from the `plan_approved` entry) with the next phase as `phase_hint`. For a build that was in `blueprint-done-revise-N`, the next phase after a SOUND G0 is `modeling`:
   ```
   append_pending_dispatch(
     protocol="<protocol>",
     target_workflow="<caller>",
     phase_hint="<next phase>",
     reason="G0 SOUND on cycle <N>"
   )
   ```
3. Clear navigate's active-workflow flag via `ivy_workflow_state(action="clear", protocol="<protocol>")` and end the turn. Navigate's Phase 1 Step 2c on the next user turn (or same turn if the harness routes the `pending_dispatch` back to navigate in-line) consumes the entry and dispatches `<caller>` with the `phase_hint`, writing the paired `workflow_resumed` marker as part of Step 2c's idempotency protocol.

Navigate does NOT call `Skill(skill="panther-ivy-plugin:<caller>")` directly here — the hand-off rides on `pending_dispatch` so the journal carries the full causal chain (`plan_approved` → `gate_verdict{SOUND}` → `pending_dispatch` → `workflow_resumed`).

### Step 6 — UNSOUND: surface and halt

If `verdict == UNSOUND`:

1. Present the dissenter reasons to the user via `AskUserQuestion` (per `feedback_askuserquestion_always`). Include the cited pattern IDs, file:line locators, and each critic's justification.
2. Offer three follow-up options:
   - **Revise the plan** — re-enter plan mode to fix the flagged issues. Phase 1.5 re-fires on the next approval (cycle counter increments, budget is 3).
   - **Overrule G0** — user authority accepts the verdict against the critics. Record a `decision` journal entry with `override_reason: <user-provided>` before re-activating the workflow.
   - **Defer** — pause without re-activation; the `plan_approved` entry remains open until the next Phase 1.5 run.
3. Do NOT re-activate the workflow on UNSOUND without explicit user input.

If the cycle count reaches 3 and the verdict is still UNSOUND, escalate: halt with a summary of all three cycles' dissenter reasons and wait for user direction. Do not auto-overrule.

### Step 7 — ABSTAIN: insufficient evidence

If `verdict == ABSTAIN`:

1. Present the abstain reasons to the user (usually "critic could not decide without X").
2. Offer to gather the missing evidence (RFC text fetch, additional file reads, wider journal scan) and re-run G0.

ABSTAIN does not consume a cycle from the 3-cycle budget; only `UNSOUND` does.

---

## Phase 2 — Branch by Context

Based on the context gathered in Phase 1, choose exactly ONE of the three branches below. Evaluate them in order and take the first match.

### Branch A: Warm Resume

**Condition:** `build-state.yaml` exists and contains an in-progress build.

1. Read the build state: workflow, protocol, methodology, layers with their completion status.
2. Infer actual progress from the file system:
   - Which `.ivy` files exist under the protocol directory
   - Run `ivy_diagnostics(mode="structural")` on recently modified files to check compilation status
3. Present a progress summary to the user:
   ```
   You're in the middle of building the [protocol] model using [methodology].
   [N/M] layers complete. Last session ended at [layer/phase context].
   Pick up where you left off? Or do something else?
   ```
4. **Skip redundant questions** — if journal contains `decision` events, present them as confirmed decisions rather than re-asking.
5. **Flag errors** — if journal contains recent `error` events, present them upfront as potential blockers.
6. Wait for user response:
   - **Pick up:** Dispatch to the appropriate workflow (usually `build`), setting the active-workflow flag via `ivy_workflow_state(action="set", workflow="<workflow_name>", phase="resume", protocol="<protocol>")`
   - **Something else:** Proceed to the user interview below, then dispatch based on their answer

### Branch B: Activity Summary

**Condition:** No `build-state.yaml`, but `git log` found recent `.ivy` changes.

1. Summarize what happened since the last session:
   ```
   Last session you [modified/created/verified] [file list].
   [Brief summary of changes from git log.]
   ```
2. Offer context-appropriate next steps:
   - If changes look like spec edits: "Want to verify these changes? Or continue working on the spec?"
   - If changes look like test additions: "Want to run the tests? Or review coverage?"
3. Wait for user response, then dispatch based on their choice.

### Branch C: Cold Start

**Condition:** Neither build state nor recent Ivy changes found.

#### Multi-Perspective Exploration — Ambiguous Goals

If the user's goal is ambiguous (no clear workflow match), load the `reflection-patterns` skill and apply **Pattern B (Multi-Perspective Exploration)** before interviewing:

- **Exploration question:** "What workflow best serves this user's needs?"
- **Agent perspectives:** Use these 3 roles instead of the defaults:
  - **Methodology Expert** (Explore): "Given the protocol and user's background, which NCT/NACT/NSCT approach fits best?"
  - **Tool Expert** (Explore): "Which tools and workflows are most relevant to what the user described?"
  - **Testing Expert** (Explore): "What kind of testing should be prioritized based on the protocol's maturity?"
- Present the synthesized recommendation to the user, then proceed with the interview.

If the user's goal is clear, skip the MPE and proceed directly to the interview.

Interview the user with 1-3 focused questions. Ask one question at a time.

1. **What protocol?** "Which protocol are you working with?" (Skip if the workspace is already set or there's only one protocol directory.)
2. **What's your goal?** "What would you like to do?" Offer concise options:
   - Build a new protocol model
   - Continue or extend an existing model
   - Verify or debug a specification
   - Review coverage or quality
   - Learn about the methodology
3. **Which methodology?** "Which testing approach?" NCT (compliance), NACT (security), or NSCT (simulation). Skip if implied by the goal or if the user seems unfamiliar with the options — default to NCT.

Dispatch based on answers.

---

## Plan-Author Branch (only when Phase 0 detected plan mode)

This branch replaces Phase 2's dispatch. Plan mode blocks state-mutating actions, so the normal workflow-dispatch path cannot run. The Plan-Author Branch gathers context, helps the user draft the plan, records an auditable handoff, and then ExitPlanMode returns control to the harness.

### Step 1 — Silent context scan (safe in plan mode)

Run Phase 1's Steps 1–3 (locate protocol, check active build, check recent `.ivy` changes) and Step 2b (check workflow journal). Skip Step 4 (triage preflight) because triage may mutate state. Gather the same context that normal navigate would — the information is still useful even though dispatch won't happen.

### Step 2 — Situation Briefing framed for plan-mode options

Load `reflection-patterns` skill and apply Pattern C (Situation Briefing) with options framed for plan authoring rather than workflow dispatch:

- "Write a plan for X" — where X is inferred from the user's opening question and the context scan.
- "Audit an existing plan" — if the user references an existing plan file.
- "Clarify scope before writing" — when the user's intent is ambiguous enough that drafting would be premature.
- "Learn before planning" — if the context suggests the user should load a methodology or syntax reference first.

### Step 3 — Draft the plan

When the user is ready to draft, help them produce the plan file at the path named in the plan-mode system-reminder (e.g., `/Users/<user>/.claude/plans/<name>.md`). If the plan involves a non-trivial implementation, invoke `Skill(skill="superpowers:writing-plans")` to apply that skill's structure. Do NOT attempt to dispatch `build`, `verify`, or `review` — they would fail under plan mode's edit restrictions.

Throughout drafting, present option-level decisions via `AskUserQuestion` (not inline prose) per the `feedback_askuserquestion_always` convention. Implementation-plan tasks should present 2–3 options per modification task per `feedback_plan_task_options`.

### Step 4 — Append `plan_approved` journal entry

Before the user calls `ExitPlanMode`, append the handoff record that Phase 1.5 will consume on the next invocation (see the `## Phase 1.5 — Post-plan-approval handoff` section above):

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

The `caller` field is best-effort: if `active-workflow` names a paused workflow, use that; otherwise infer from the user's opening intent. The `supersedes` array is populated from a `## Supersedes` block in the plan file, if present.

### Step 5 — ExitPlanMode

Call `ExitPlanMode` to return control to the harness. Navigate's Phase 1.5 (the `## Phase 1.5 — Post-plan-approval handoff` section above) fires on the next user turn to dispatch G0 and re-activate the caller workflow.

---

## Dispatch

### Reflection Gate — Pre-Dispatch Check

Load the `reflection-patterns` skill. Apply **Pattern A (Reflection Gate)** with this context:

- **Current state:** Summarize the branch taken in Phase 2 and the workflow about to be dispatched.
- **Alternative workflows:** Name 1-2 alternatives and why they might be relevant.
- **Example:** If dispatching to `build` but the user mentioned "test" or "verify" in their last message, offer `verify` as an alternative.

After the user confirms, proceed with dispatch.

When dispatching to a workflow:

1. Call `ivy_workflow_state(action="set", workflow="<workflow_name>", phase="init", protocol="<protocol>")` to write the active-workflow flag.
2. Invoke the workflow: `Skill(skill="{workflow_name}")`

### Routing Table

| Goal | Dispatch Target |
|------|----------------|
| Build or scaffold a protocol model | `build` workflow |
| Verify or debug a specification | `verify` workflow |
| Review quality or coverage | `review` workflow |
| Diagnose broken tools | `triage` workflow |
| Learn methodology | `methodology-reference` skill |
| Extract RFC requirements | `traceability-agent` agent |

If the user's goal doesn't clearly map to a workflow, ask one clarifying question before dispatching.

---

## Integration

- **Called by:** Session start (routing hook), other workflows on completion
- **Calls:** `triage` (preflight, skipped under plan mode), then dispatches to `build`, `verify`, `review`, or skills/agents. Plan-Author Branch may call `superpowers:writing-plans`.
- **Knowledge skills loaded:** `reflection-patterns` (SB after Phase 1, RG before dispatch, MPE on cold start, Plan-Author Step 2), `knowledge-capture` (KG after Phase 1)
- **State files:** `.panther-ivy/active-workflow`, `.panther-ivy/build-state.yaml`
- **Infrastructure:** `ivy_workflow_state` MCP tool for state reads/writes; `track-workflow-skill.py` PostToolUse hook for automatic state on skill activation
- **MCP tool reliability:** on `InputValidationError` or any `ivy_*` MCP-tool failure, follow the canonical recovery pattern in `.claude/rules/mcp-tool-reliability.md` (ToolSearch retry-once, then AskUserQuestion with triage / skip / abandon options).

### Journal entry types this skill produces or consumes

| Type | Direction | Introduced by |
|------|-----------|---------------|
| `context_switch` | produces (Phase 0 detection) | Phase 0 |
| `plan_approved` | produces (Plan-Author Step 4) | Plan-Author Branch |
| `pending_dispatch` | consumes (Phase 1 Step 2c) | Any workflow emitting a hand-off |
| `workflow_resumed` | produces (Phase 1 Step 2c + Phase 1.5 Step 5) | Pending-dispatch consumption + post-plan-approval handoff |
| `gate_verdict` with `gate: "g0"` | produces (Phase 1.5, via `reflection-patterns` G0 dispatch) | Post-plan-approval handoff |
| `decision`, `phase_transition`, `session_start`, `session_end`, `error`, `progress` | both | Existing schema (unchanged) |

Full schema for each type lives in the `reflection-patterns` skill's `references/gates.md` (gate_verdict payload) and in `superpowers:writing-plans` (plan file conventions consumed by the `supersedes` extraction, when that plugin is installed).
