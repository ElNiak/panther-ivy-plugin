---
name: reflection-patterns
description: "Reflection and adversarial-gate patterns for workflow boundaries: Reflection Gate, Multi-Perspective Exploration, Situation Briefing, Completion Verification, and quality gates. Use when dispatching gate critics or at phase transitions."
user-invocable: false
context: fork
---

# Interaction Patterns

Three reusable patterns for structured user interaction during workflows. Each workflow skill references a specific pattern at designated points.

---

## Pattern A: Reflection Gate (RG)

A structured pause to re-evaluate whether the current workflow still matches the user's intent.

**When invoked, do these steps in order:**

1. **Summarize** the current state in 2-3 sentences: what phase you are in, what was found so far, what is pending.

2. **Re-evaluate** workflow fit by checking three signals:
   - Has the user's recent language shifted toward a different workflow's domain? (e.g., asking about coverage during a verify workflow suggests switching to review)
   - Did findings suggest a different workflow would be more appropriate? (e.g., structural issues during verify suggest switching to build)
   - Are you in a dead-end loop? (same error encountered twice with no progress)

3. **Present options** via `AskUserQuestion` with 2-3 choices:
   - **(a)** Continue the current path — explain what happens next
   - **(b)** Switch to [named alternative workflow] — explain why it might be better, based on the signals above
   - **(c)** Pause and explain more — provide deeper context before the user decides

4. **Act on choice**:
   - If (a): proceed with the next phase of the current workflow
   - If (b): emit `append_pending_dispatch(target_workflow=<new>, reason=<why>)` on the journal, clear `active-workflow` via `ivy_workflow_state(action="clear")`, and end the turn — navigate will consume the `pending_dispatch` event and dispatch the new workflow
   - If (c): provide the expanded explanation, then re-present the choice

Pattern A fires unconditionally at every designated insertion point. There is no "sub-workflow skip" — workflow composition rides on `pending_dispatch` journal events, so each workflow is a top-level frame from the state machine's perspective. The old `invocation_depth > 0` skip-check is removed.

---

## Pattern B: Multi-Perspective Exploration (MPE)

Dispatch 2-3 parallel agents with divergent perspectives to explore a decision point before committing.

**When invoked, do these steps in order:**

1. **Define the exploration question**: State clearly what decision needs to be made (e.g., "Which architectural approach for this protocol model?" or "What is the root cause of this verification failure?").

2. **Dispatch agents in parallel** using multiple Agent tool calls in a single message. Use 2-3 of these perspective agents:

   | Agent | Role | Method | Focus Question | subagent_type |
   |-------|------|--------|---------------|---------------|
   | **Conservative Architect** | Safety-first formal methods expert | Top-down: decompose from spec requirements down to implementation constraints | "What could go wrong? What's missing?" | `Explore` |
   | **Pragmatic Engineer** | Velocity-focused builder | Bottom-up: start from working code and existing patterns, build abstractions only when needed | "What's the fastest path to a working result?" | `Explore` |
   | **Adversarial Auditor** | Red-team antagonist | Stress-test: actively try to break the current approach, find edge cases, question assumptions | "Where does this break? What assumptions are wrong?" | `Explore` |

   When an MPE slot maps to an existing agent definition whose specialization matches (e.g., `spec-analyst` for verification analysis, `model-reviewer` for structural audit), use that agent's `subagent_type` instead.

   Each agent prompt must follow this template:

   ```
   You are the {ROLE_NAME} reviewing {CONTEXT}.

   **Your role**: {ROLE_DESCRIPTION}
   **Your method**: {METHOD_DESCRIPTION}
   **Your focus question**: {FOCUS_QUESTION}

   Context:
   - Current workflow: {workflow}
   - Current phase: {phase}
   - Protocol: {protocol}
   - Key findings so far: {findings_summary}
   - Files involved: {file_list}

   Produce a short analysis (under 300 words) with:
   1. **Assessment**: What do you see in the current state?
   2. **Recommendation**: What should we do next and why?
   3. **Risks**: What could go wrong with your recommendation?
   4. **Dissent**: Where might the other reviewers disagree with you?
   ```

3. **Synthesize** after all agents return:
   - Identify agreement points (where 2+ agents converge)
   - Highlight disagreements (where agents diverge, with each perspective's reasoning)
   - Note unique insights (observations only one agent raised)

4. **Present to user** via `AskUserQuestion` with options derived from agent recommendations:
   - Option per distinct recommendation (max 4)
   - Include which agent(s) support each option and why

5. **Proceed** with the user's chosen direction.

---

## Pattern C: Situation Briefing (SB)

Explain the current situation and confirm the next step before proceeding.

**When invoked, do these steps in order:**

1. **Explain** the current situation in plain language:
   - What happened in the previous phase (1-2 sentences)
   - What was found: key results, metrics, or issues (be specific — numbers, file names, pass/fail)
   - What it means for the user's goal (so what?)

2. **Present options** for the next step via `AskUserQuestion` with 2-4 choices. Each option must include:
   - What it involves (concrete action)
   - Expected outcome (what you'll have after)
   - Trade-off (time, coverage, risk — one sentence)

3. **Proceed** with the user's chosen option.

---

## Pattern D: Completion Verification Gate (CVG)

A mandatory gate before any workflow transitions to complete or returns to navigate.

**When invoked, do these steps in order:**

1. **Re-run verification** — `ivy_diagnostics(mode="structural")` + `ivy_verify` on all files modified during this workflow session. Results must be from THIS turn, not cached from earlier.

2. **Anti-pattern checklist** — verify each item:
   - `after init` present for all mutable relations
   - No ungrounded variables in invariants
   - `require` used instead of `assume` (unless user-justified)
   - `require` present in all `before` clauses
   - No circular include dependencies
   - `export _finalize` present if end-state checks needed

3. **Coverage delta** — If the workflow added monitors or assertions, run `ivy_coverage(mode="stats")` and confirm coverage did not regress.

4. **Gate**: Only transition to complete if all three pass. If any fails, stay in current phase and report the failure to the user.

---

## Adversarial Quality Gates (G0–G5) — Discipline Layer atop MPE/CVG

Pattern B (MPE) and Pattern D (CVG) provide the dispatch substrate for the plugin's adversarial quality gates. Six gates fire at lifecycle decision points and produce calibrated verdicts (`SOUND` / `UNSOUND(#NN, …)` / `ABSTAIN`) instead of free-form analysis. Each gate uses a context-isolated MPE fan-out with four discipline contracts that bind how critics are spawned and how their votes are aggregated.

| # | Gate | Lifecycle step | Workflow + insertion |
|---|---|---|---|
| G0 | plan | post-ExitPlanMode, pre-workflow-resume | `navigate` post-plan-approval handoff / `build` parallel entry |
| G1 | exploration | scope + blueprint | `build` after Phase 2, before Phase 3 |
| G2 | per-layer modeling | each `.ivy` layer write | `build` Phase 3 |
| G3 | test-spec | each test-spec write | `build` Phase 3 (test sub-step) |
| G4 | verification | after `ivy_verify` returns | `verify` Phase 4 |
| G5 | trace analysis | after `ivy_iut_test` returns | `verify` Phase 5 |

**Full gate specifications — discipline contracts, per-gate critic templates, tier configuration, verdict persistence schema, GAP-marker conventions, and catalog-slice routing — live in `references/gates.md`.** Load that reference when dispatching any gate. Tier defaults and thresholds live in `references/model_tier_defaults.md`.

Per-gate critic prompts live under `references/critic_prompts/`: `g0_plan.md`, `g1_exploration.md`, `g2_modeling.md`, `g3_testspec.md`, `g4_verification.md`, `g5_trace.md`. Load the relevant template verbatim when spawning a critic — the first three paragraphs of every template are load-bearing.

---

## Integration Notes

- Workflow skills load this knowledge skill via `Skill(skill="reflection-patterns")` when they reach a designated interaction point.
- The calling workflow specifies which pattern (RG, MPE, or SB) and provides the workflow-specific context (phase, findings, protocol, files).
- This skill is loaded into a fork context — it does not persist across turns.
