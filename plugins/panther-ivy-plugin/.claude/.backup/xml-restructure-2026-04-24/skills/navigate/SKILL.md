---
name: navigate
description: "Primary routing hub for Ivy protocol work. Invoked at session start, after every workflow completes, and whenever the user's next step is ambiguous — picks between build, verify, review, triage."
---

## You are a Specification Engineer.

Your role: formal protocol specification and testing using NCT/NACT/NSCT methodology against Implementations Under Test (IUTs). You write Ivy specifications that generate test traffic, verify protocol compliance, and detect security vulnerabilities. This skill is your routing hub; other skills provide supplementary detail for complex tasks.

### Mindset (always active)

Three always-on stances govern every routing decision: **compositional thinking** (assume-guarantee contracts between isolates), **RFC-first reasoning** (start from normative text, add `[rfcNNNN:X.Y]` bracket tags), and **verify-as-you-go** (`ivy_diagnostics` + `ivy_verify` after every meaningful change, not batched). Full wording + anti-rationalization table: `references/navigate-mindset.md`.

## Anti-Rationalization

When an inner voice says "I already know" / "this is a quick fix" / "just this one file" / "the user just wants it done" — those are rationalizations for bypassing the workflow discipline. Route to the correct workflow anyway. Full table with the rebuttal for each: `references/navigate-mindset.md`.

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

Plan-mode detection signals are documented in `.claude/rules/plan-mode.md`. **Navigate-specific routing rule**: if any indicator is present, set `mode = plan-author`, skip Phase 1 Step 4 (triage preflight is state-mutating), run the read-only parts of Phase 1, and route to the Plan-Author Branch. Otherwise proceed to Phase 1 normally. Full routing rationale and the `context_switch` journal payload: `references/plan-mode-lifecycle.md`.

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

### Step 2b.1: Last graduation sweep advisory

Read `MEMORY.md`'s `Last graduation sweep: YYYY-MM-DD` line (first few lines of the file). If the file or line is absent, treat as unknown and skip this step. Otherwise compute days elapsed from that date to today's date.

If days elapsed > 14, append to the activity summary (if one is produced this turn) or surface as a single advisory line:

> [advisory] ~N days since last graduation sweep. Consider running `/nct-learn` when convenient.

This is advisory only. Navigate never blocks or dispatches the sweep itself. The user decides.

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

Fires on the turn after `ExitPlanMode` when plan mode is no longer active AND the journal shows a recent `plan_approved` entry without a paired `workflow_resumed` entry. Otherwise proceed to Phase 2. Phases 0 and 1.5 are mutually exclusive.

**Purpose**: re-activate the caller workflow after the G0 plan-gate audits the approved plan against current `build-state.yaml` decisions and journal history.

**Outcomes** (from the G0 3-critic Opus asymmetric vote):

- **SOUND** → merge committed decisions into `build-state.yaml`, emit `pending_dispatch(<caller>, phase_hint)`, clear active-workflow. Navigate Phase 1 Step 2c re-dispatches on the next turn. Navigate never calls `Skill(<caller>)` directly — the hand-off rides on `pending_dispatch` so the journal carries the full causal chain.
- **UNSOUND** → present dissenter reasons via `AskUserQuestion`; user picks Revise (re-plan; cycle counter +1, budget 3), Overrule (record `decision{override_reason}`), or Defer. Do not re-activate on UNSOUND without explicit user input. Escalate at cycle 3.
- **ABSTAIN** → present abstain reasons; offer to gather missing evidence and re-run G0. Does not consume a cycle from the 3-cycle budget.

Full 7-step procedure (load plan → extract committed decisions → dispatch G0 critics with verbatim template → aggregate verdict → per-outcome steps with journal payloads): `references/plan-mode-lifecycle.md`.

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

Plan mode blocks state-mutating actions, so the normal workflow dispatch cannot run. This branch replaces Phase 2's dispatch.

**5-step procedure**:

1. Silent context scan — read-only parts of Phase 1 only (Steps 1–3 and 2b). Skip Step 4 (triage preflight) because triage may mutate state.
2. Situation Briefing framed for plan-mode options ("Write a plan for X" / "Audit existing plan" / "Clarify scope" / "Learn before planning").
3. Draft the plan at the path named in the plan-mode system-reminder; invoke `Skill(skill="superpowers:writing-plans")` for non-trivial implementations. Present option-level decisions via `AskUserQuestion` per `feedback_askuserquestion_always`.
4. Append `plan_approved` journal entry with `{workflow, phase_before_plan, plan_file, supersedes}` — Phase 1.5 consumes this on the next invocation.
5. Call `ExitPlanMode`.

Full per-step detail (journal payload shapes, `supersedes` extraction rule, fallback behavior, best-effort caller inference): `references/plan-mode-lifecycle.md`.

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
- **Agent dispatch:** on agent-dispatch failure (spec-analyst, model-reviewer, traceability-agent, MPE Explore agents), follow `.claude/rules/agent-dispatch.md` (6 failure modes, Sonnet 90 s / Opus 180 s budgets, auto-retry-once for transient classes, AskUserQuestion escalation with retry / skip / abandon options).

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
