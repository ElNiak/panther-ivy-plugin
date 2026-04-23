---
name: review
description: "RFC requirement-to-monitor traceability, coverage audits, and model quality review for Ivy specs. Use when user asks \"what MUSTs am I missing?\", \"RFC coverage?\", \"traceability gap?\", or \"review my model\"."
---

## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
the active workflow overlay and phase modifier. Do not invent
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.

## Phase 0 — Plan-mode preamble

Before running any review-phase logic, inspect the session context for plan-mode indicators. Plan mode blocks `ivy_coverage`, `ivy_quality`, and any tool that mutates state, so the normal review cycle cannot proceed.

Detection signals (any one is sufficient):

1. The literal phrase `Plan mode is active` in a system-reminder.
2. The edit-restriction phrase `You MUST NOT make any edits`.
3. A plan file path of the form `/Users/*/plans/*.md` named in a plan-mode system-reminder.

If any indicator is present, switch to plan authoring instead of review dispatch:

1. Run read-only context gathering only: check the workflow journal for recent `error`, `gate_verdict`, and `decision` entries; skip any step that would mutate state.
2. Present a situation briefing via `AskUserQuestion` framed for plan-mode options — "draft a plan to close specific RFC coverage gaps", "draft a plan to refactor the model quality issues we found", "clarify the review scope before writing", "learn the coverage/traceability conventions first".
3. Help the user draft the plan at the path named in the plan-mode system-reminder. If the plan covers a non-trivial implementation, invoke `Skill(skill="superpowers:writing-plans")`.
4. Before `ExitPlanMode`, append a `plan_approved` journal entry with `workflow: "review"`, `phase_before_plan: <whatever phase the user was in>`, `plan_file`, and `supersedes` (extracted from the plan's `## Supersedes` block if present).
5. Call `ExitPlanMode`.

Do NOT attempt to dispatch `ivy_coverage`, `ivy_quality`, `ivy_extract_requirements`, or any state-mutating tool during plan mode — the call will be rejected and the session ends in an ambiguous state. Navigate's Phase 1.5 handles the re-entry on the next invocation after `ExitPlanMode`.

## Iron Laws

This skill is bound by `NO_QUALITY_WITHOUT_COVERAGE` and the `STALENESS RULE`. Before exiting Phase 0 (Plan-mode preamble) and entering Phase 1 (Triage), Read `.claude/rules/iron-laws.md` for the canonical wording and the explicit non-targets (style/naming feedback, readability comments, design alternatives are allowed without tool citations — they are not "quality verdicts"). Summary for this skill: before stating a formal coverage or quality verdict, cite `ivy_coverage` and/or `ivy_quality` output from the current turn inline.

## Step Tracking

At the start of each phase, create tasks for each step using `TaskCreate`.

Phase 1 (Triage):
```
TaskCreate(subject="Classify review type", activeForm="Classifying review type")
TaskCreate(subject="Detect target protocol", activeForm="Detecting protocol")
TaskCreate(subject="Run triage preflight", activeForm="Running triage preflight")
```

Phase 2 (Dispatch) with dependencies:
```
TaskCreate(subject="Quality audit (model-reviewer)")        → task A
TaskCreate(subject="Coverage audit (traceability-agent)")   → task B
TaskUpdate(taskId=B, addBlockedBy=[A])
```

Phase 3 (Resolution):
```
TaskCreate(subject="Present findings to user", activeForm="Presenting findings")
TaskCreate(subject="Resolve contested findings", activeForm="Resolving findings")
TaskCreate(subject="Run Completion Verification Gate", activeForm="Running completion gate")
```

Do not skip marking tasks as `completed`.

# Review Workflow

Read `.panther-ivy/active-workflow` on every turn to determine the current phase. Update the phase field on transition.

## Journal Requirements

Throughout this workflow, record state changes to the workflow journal:

- **Decisions**: When making or confirming a design/implementation choice (e.g., deferring a requirement, choosing layer order, selecting methodology), immediately call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="decision", state='{"summary": "<what was decided>", "context": "<why>"}')`

- **Progress**: After completing a meaningful sub-step (e.g., "compiled 3/8 layers", "fixed 2 verification failures"), call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="progress", state='{"detail": "<what completed>"}')`

These journal entries enable warm session resume and decision traceability across sessions.

---

## Phase 1 — Triage

### Step 1: Detect review type

Classify the user's intent into one of three review types:

| Review Type | Trigger Keywords |
|-------------|-----------------|
| **Coverage** | "RFC gaps", "how much do I cover", "coverage", "traceability", "requirements" |
| **Quality** | "review my model", "issues", "quality", "check for problems", "audit" |
| **Both** | Ambiguous request, or user explicitly asks for both |

### Step 2: Detect target protocol

Resolve the protocol in this order:

1. Check the active workspace via `ivy_workspace(action="get")`
2. Check `IVY_WORKSPACE_ROOT` environment variable
3. Scan the current working directory for `protocol-testing/` subdirectories

If still ambiguous, ask: "Which protocol should I review?"

### Step 3: Run triage preflight (inline)

Confirm MCP/LSP health before dispatching review agents. Preflight is a read-only skill call with no state writes:

```
Skill(skill="panther-ivy-plugin:triage", args="preflight")
```

Triage runs Phase 1 only and returns to review's current turn. `active-workflow` stays on `(workflow=review, phase=triaged)` throughout. On healthy: triage returns silently. On failure: triage escalates to Phase 2–3 interactively; on repair completion it emits `pending_dispatch(review, reason="post-triage-repair")` so navigate re-activates review on the next turn.

### Situation Briefing — Review Type Confirmation

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)**:

- **What happened:** "Detected review type: [Coverage / Quality / Both]. Protocol: [protocol]. Stack health: [passed / required intervention]."
- **What it means:** Explain what this review type will check and approximately how long it takes.
- **Options:** "Proceed with [detected type] review" / "Switch to [other type]" / "Run both coverage and quality"

### Step 4: Update state

Update phase to `"triaged"` via `ivy_workflow_state(action="set", workflow="review", phase="triaged", protocol="<protocol>")`.

---

## Phase 2 — Execute

Branch by the review type detected in Phase 1.

### Coverage Path

Dispatch the `traceability-agent` agent:

1. The agent extracts RFC requirements from existing manifests, or reads `build-state.yaml` for the target RFC(s).
2. The agent scans `.ivy` files for bracket-tag annotations (`# [rfcNNNN:X.Y]`).
3. The agent reports coverage by priority:
   - MUST requirements: covered/total
   - SHOULD requirements: covered/total
   - MAY requirements: covered/total
4. The agent lists gaps ordered by priority (uncovered MUST first).

### Quality Path

#### Multi-Perspective Exploration — Quality Analysis

Load the `reflection-patterns` skill. Apply **Pattern B (Multi-Perspective Exploration)** with 3 agents:

- **Exploration question:** "What are the quality issues in this protocol model?"
- **Agents (dispatch all 3 in parallel):**
  - **model-reviewer** (use `subagent_type: "panther-ivy-plugin:model-reviewer"`): 6-category structural audit (structural, type safety, invariants, actions, initialization, organization)
  - **spec-analyst** (use `subagent_type: "panther-ivy-plugin:spec-analyst"`): Verification readiness, include trace, layer coherence
  - **Adversarial Auditor** (use `subagent_type: "Explore"`): Red-team the model — find edge cases the structured audits miss, question assumptions in the spec, identify states that could be reached but aren't tested

Synthesize findings from all 3 agents before presenting. Dispatch all three agents IN PARALLEL (three Agent tool calls in one message):

**model-reviewer** runs a 6-category structural audit:

1. Structural correctness (headers, includes, circular deps)
2. Type safety (annotations, mismatches, enumerations)
3. Invariant completeness (ungrounded vars, missing invariants, strength)
4. Action well-formedness (preconditions, postconditions, guards)
5. Initialization (`after init` blocks, consistency with invariants)
6. Organization (naming, isolate boundaries, duplication)

**spec-analyst** checks:

1. Verification readiness (will `ivy_verify` pass?)
2. Include trace correctness (resolved paths, missing modules)
3. Layer coherence (are layers used consistently with the 14-layer template?)

Aggregate findings from both agents by severity: critical, important, suggestion.

### Both Paths

Run coverage and quality paths in parallel. Aggregate all findings into a unified report.

### Update state

Update phase to `"executed"` via `ivy_workflow_state(action="set", workflow="review", phase="executed", protocol="<protocol>")`.

### Knowledge Gate: Post-Agent-Execution

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on cross-model patterns identified by model-reviewer and traceability-agent
- Capture any recurring quality findings worth remembering
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Phase 3 — Findings

### Step 1: Present findings

Present findings with severity classification (per `.claude/rules/ivy-formatting.md` Severity Systems — "Finding severity"):

- **ERROR:** Verification will fail, or the model is unsound. Must fix before committing.
- **WARNING:** Quality concern that a code reviewer would flag. Should fix.
- **INFO:** Improvement that doesn't affect correctness.

Load the `claim-discussion` knowledge skill for structured discussion of any contested findings.

### Gate checkpoint on ERROR findings

If ERROR findings were produced: "These ERRORs were found: [list]. Fix them now? Run verify on flagged files?"

Wait for explicit confirmation.

### Reflection Gate — Post-Findings Direction

Load the `reflection-patterns` skill. Apply **Pattern A (Reflection Gate)**:

- **Current state:** "[N] critical, [N] important, [N] suggestion findings across [coverage/quality/both] analysis."
- **Re-evaluate:** Do the findings suggest a different workflow is needed?
  - Many structural issues — `build` workflow to fix the model architecture
  - Verification failures — `verify` workflow to diagnose specific failures
  - Coverage gaps only — stay in `review` to address gaps
- **Alternative workflows:** `build` (structural fixes), `verify` (targeted verification), stay in `review` (address findings inline)

### Step 2: Handle user response

**If the user wants fixes:**

Adversarial gates G2 (layer modeling) and G3 (test-spec) do NOT fire on review-inline fixes — they are build-time gates by design. For structural concerns that warrant G2/G3 re-run, dispatch back to `build` via `append_pending_dispatch(target_workflow="build", phase_hint="layer-check")` and clear the active-workflow flag; review is for audit, not construction. Load `reflection-patterns` and read its `references/gates.md` "G2/G3 workflow scope" section for the canonical rationale.

Guide fixes inline using the relevant agent's recommendations. After applying fixes, re-run the analysis that found the issue to confirm resolution.

After any `Write` / `Edit` on a `.ivy` file during this inline-fix path, inspect the tool-result for a workspace-scope violation from the `check-workspace-scope.py` PreToolUse hook. If blocked, append `progress{kind: "workspace_edit_blocked", file: "<path>", workspace_active: "<current>"}` to the journal and present `AskUserQuestion` with three options per `.claude/rules/mcp-tool-reliability.md`: switch workspace to the file's protocol (run `/set-workspace <inferred>`), clear workspace restrictions (run `/clear-workspace`), or abandon this fix and record a `decision` entry.

**If the user wants verification:**

Emit a `pending_dispatch` naming `verify` and let navigate route the hand-off on the next turn — review does not dispatch verify directly:

```
append_pending_dispatch(
  protocol="<protocol>",
  target_workflow="verify",
  reason="review Phase 3 — user requested targeted verification of flagged findings"
)
```

Then clear the active-workflow flag via `ivy_workflow_state(action="clear", protocol="<protocol>")` and end the turn. Navigate's Phase 1 Step 2c consumes the entry and dispatches `verify`. On verify's completion it may emit `pending_dispatch(review, phase_hint="findings")` to hand control back — review then re-enters with the verify outcome readable from the journal (`gate_verdict`, `progress`).

**If the user accepts as-is:**

Proceed to completion.

### Knowledge Gate: Post-Findings-Resolution

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on workflow refinements from the resolution process
- Capture fix strategies that worked or didn't work
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## On Completion

Before completing, apply **Pattern D (Completion Verification Gate)** from the `reflection-patterns` skill.

If this review run needs another workflow to run next (e.g., the user asked for targeted verification on a flagged finding), append `pending_dispatch(<next>, reason=<why>)` first. Then clear the active-workflow flag via `ivy_workflow_state(action="clear", protocol="<protocol>")`. Navigate's Phase 1 Step 2c consumes any pending dispatch on the next user turn. If no hand-off is needed, simply clear the flag — navigate re-activates on the next user turn.

---

## Integration

- **Called by:** `navigate` (dispatch), `build` (quality gate — though build dispatches agents directly), `verify` (follow-up coverage), user directly ("review my model", "check coverage")
- **Calls:** `triage` (preflight), `traceability-agent` agent (coverage), `model-reviewer` agent (quality), `spec-analyst` agent (quality), `verify` workflow (optional follow-up)
- **Knowledge skills loaded:** `reflection-patterns` (SB Phase 1, MPE Phase 2, RG Phase 3), `claim-discussion` (Phase 3 for contested findings), `knowledge-capture` (KG Phase 2, KG Phase 3)
- **MCP tools used:** `ivy_workspace` (protocol detection)
- **State files:** `.panther-ivy/active-workflow`
- **MCP tool reliability:** on `InputValidationError` from `ivy_coverage` / `ivy_quality` / `ivy_extract_requirements`, follow `.claude/rules/mcp-tool-reliability.md` — one retry via `ToolSearch({query: "select:<tool>"})`, then AskUserQuestion with triage / skip / abandon options.
- **Agent dispatch:** review dispatches `traceability-agent` (Phase 2 coverage path), `model-reviewer` + `spec-analyst` + MPE Explore agents (Phase 2 quality path). On dispatch failure follow `.claude/rules/agent-dispatch.md`. Per-agent Failure Modes sections override default budgets.
