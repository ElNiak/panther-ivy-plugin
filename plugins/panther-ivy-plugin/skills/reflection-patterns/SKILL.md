---
name: reflection-patterns
description: "Structured interaction templates (Reflection Gate, Multi-Perspective Exploration, Situation Briefing, Completion Verification Gate) and the adversarial quality-gate discipline layer. Use when a workflow skill reaches a phase boundary needing user input, or when dispatching G1-G5 adversarial critics."
user-invocable: false
context: fork
---

# Interaction Patterns

Three reusable patterns for structured user interaction during workflows. Each workflow skill references a specific pattern at designated points.

---

## Pattern A: Reflection Gate (RG)

A structured pause to re-evaluate whether the current workflow still matches the user's intent.

**When invoked, do these steps in order:**

1. **Skip check**: If `invocation_depth > 0` (this workflow was called as a sub-workflow), skip this Reflection Gate entirely. Sub-workflows must not interrupt their parent's flow.

2. **Summarize** the current state in 2-3 sentences: what phase you are in, what was found so far, what is pending.

3. **Re-evaluate** workflow fit by checking three signals:
   - Has the user's recent language shifted toward a different workflow's domain? (e.g., asking about coverage during a verify workflow suggests switching to review)
   - Did findings suggest a different workflow would be more appropriate? (e.g., structural issues during verify suggest switching to build)
   - Are you in a dead-end loop? (same error encountered twice with no progress)

4. **Present options** via `AskUserQuestion` with 2-3 choices:
   - **(a)** Continue the current path — explain what happens next
   - **(b)** Switch to [named alternative workflow] — explain why it might be better, based on the signals above
   - **(c)** Pause and explain more — provide deeper context before the user decides

5. **Act on choice**:
   - If (a): proceed with the next phase of the current workflow
   - If (b): update the `active-workflow` state file to the new workflow and invoke it via `Skill(skill="{workflow_name}")`
   - If (c): provide the expanded explanation, then re-present the choice

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

## Adversarial Quality Gates (G1–G5) — Discipline Layer atop MPE/CVG

Pattern B (MPE) and Pattern D (CVG) provide the dispatch substrate for the plugin's adversarial quality gates. Five gates fire at lifecycle decision points and produce calibrated verdicts (`SOUND` / `UNSOUND(#NN, …)` / `ABSTAIN`) instead of free-form analysis. Each gate uses a context-isolated MPE fan-out with four discipline contracts that bind how critics are spawned and how their votes are aggregated.

### The five gates

| # | Gate | Lifecycle step | Workflow + insertion | Hook event |
|---|---|---|---|---|
| G1 | exploration | scope + blueprint | `build` after Phase 2, before Phase 3 | UserPromptSubmit + post-blueprint |
| G2 | per-layer modeling | each `.ivy` layer write | `build` Phase 3 | PostToolUse on `Write\|Edit` of `*.ivy` |
| G3 | test-spec | each test-spec write | `build` Phase 3 (test sub-step) | PostToolUse on `Write\|Edit` of `*_test_*.ivy` |
| G4 | verification | after `ivy_verify` returns | `verify` Phase 4 | PostToolUse on `ivy_verify` |
| G5 | trace analysis | after `ivy_iut_test` returns | `verify` Phase 5 | PostToolUse on `ivy_iut_test` |

### The four discipline contracts

These are the constraints that turn an MPE fan-out into an adversarial quality gate. The orchestrator (the workflow phase code or the wiring hook) MUST honor all four.

1. **Verbatim spawn prompts.** Load the per-gate critic prompt template from `references/critic_prompts/g{N}.md` and pass it to the `Agent` tool unmodified. Do not paraphrase, do not concatenate with chat history, do not synthesize an alternative. The first three paragraphs of every template are load-bearing — a session that rewrites them produces critics that grind and confidently get wrong answers.

2. **Dual context isolation.** Each critic sees only `(RFC clause(s) + the artifact + the catalog slice)`. It does not see the chat history, the design rationale, or sibling critics' verdicts. The orchestrator's spawn prompt is built from a single template render — no concatenation of upstream conversation.

3. **Asymmetric vote with pigeonhole exit.** Aggregate critic verdicts using the gate's tier configuration (see `references/model_tier_defaults.md`). Default Sonnet × 5: `≥4 SOUND` → `VERDICT_SOUND`; `≥2 UNSOUND` → `VERDICT_UNSOUND`; otherwise → `VERDICT_ABSTAIN`. Stop spawning once a threshold is mathematically locked.

4. **Calibrated abstention as a structured verdict.** `VERDICT_ABSTAIN` is a first-class output, not a fallback to silence. It records which critics said what, why no threshold cleared, and a recommended next step (collect more evidence, consult user, or escalate to Opus).

### Per-gate templates

The five verbatim templates live under `references/critic_prompts/`:

- `g1_exploration.md` — audits `build-state.yaml` + RFC scope; catalog slice `#100-149` + (`#150-199` if NACT) + `#250-299`
- `g2_modeling.md` — audits a just-written `.ivy` layer file; catalog slice `#200-249` + `#250-299` + (`#260-265` if NSCT)
- `g3_testspec.md` — audits a `*_test_*.ivy` file with the requirement manifest and coverage matrix; catalog slice `#200-208` + `#256-259` + `#300-399`
- `g4_verification.md` — audits an `ivy_verify` JSON return + the verified spec; catalog slice `#200-249` + `#250-299` + `#400-499`
- `g5_trace.md` — audits IUT run artifacts (analysis JSON, Ivy trace, IUT log, pcap); catalog slice `#100-107` + `#500-559` + (`#560-589` if NSCT)

### Tier configuration

`references/model_tier_defaults.md` holds the per-tier and per-gate critic counts and thresholds. The orchestrator reads `CLAUDE_MODEL_TIER` (`haiku` | `sonnet` | `opus`); if unset, defaults to Sonnet.

### Verdict persistence

Two new event types coexist in the workflow journal — no new state file required:

- **`gate_dispatched`** — written by the gate hook (`assess-modeling.py`, `assess-testspec.py`, `assess-trace.py`, the G4 branch of `record-workflow-error.py`, and the G1 branch of `route-user-prompt.py`) at the moment a gate is triggered, before any critic spawns. The breadcrumb lets the journal show which gates fired even if Claude never dispatches the critics. Payload: `{gate, trigger, artifact?, layer?, methodology?, ...}`.
- **`gate_verdict`** — written by Claude (the orchestrator) after the critic fan-out completes and the asymmetric vote has resolved. Payload schema:

```
ivy_workflow_state(
  action="append_journal",
  workflow=<active workflow>,
  phase=<gate insertion phase>,
  event_type="gate_verdict",
  payload={
    "gate": "g{1..5}",
    "verdict": "SOUND" | "UNSOUND" | "ABSTAIN",
    "vote": {"sound": int, "unsound": int, "unsure": int},
    "patterns": [{"id": "#NN", "file": "...", "line": int, "reason": "..."}],
    "abstain_reason": "..." | null,
    "tier": "haiku|sonnet|opus",
    "duration_s": float
  }
)
```

Both types appear alongside the existing `phase_transition`, `context_switch`, `error`, `decision`, `progress`, `session_start`, `session_end`. They are whitelisted in `_VALID_EVENT_TYPES` in both the local `workflow_state.py` helper and the MCP tool's `workflow_state.py` so writes are accepted.

### GAP markers

On `VERDICT_UNSOUND`, the orchestrator (never a critic) writes `[GAP: #NN <reason>]` markers inline at the cited file:line locations using `Edit`. The full convention — relationship to existing `claim-discussion` resolution prefixes (`RESOLVED`, `IUT_FINDING`, `DEFERRED`, `GUARD_ADDED`, `KNOWN_DEVIATION`, `N/A`), promotion rules, and listing/grep commands — lives in `.claude/rules/gap-markers.md`.

### Catalog

The `ivy-error-patterns` skill owns the numbered, append-only catalog (`verifier_patterns.md`). Sparse IDs preserve provenance; do not renumber. NACT entries (#150-199) load when `build-state.yaml:methodology` is `nact`; NSCT entries (#260-289 and #560-589) load when methodology is `nsct`.

Cross-skill access: each critic's verbatim spawn prompt instructs the critic to load the `ivy-error-patterns` skill via the Skill tool, which makes the catalog available. The critic then reads only entries in its assigned ID range. The spawning agent must have the Skill tool and `ivy-error-patterns` available — either through its `subagent_type` tool set or by declaring `skills: [ivy-error-patterns]` in the agent's frontmatter.

---

## Integration Notes

- Workflow skills load this knowledge skill via `Skill(skill="reflection-patterns")` when they reach a designated interaction point.
- The calling workflow specifies which pattern (RG, MPE, or SB) and provides the workflow-specific context (phase, findings, protocol, files).
- This skill is loaded into a fork context — it does not persist across turns.
