# Adversarial Quality Gates (G0–G5)

Discipline layer atop Pattern B (Multi-Perspective Exploration) and Pattern D (Completion Verification Gate) in `SKILL.md`. Six gates fire at lifecycle decision points and produce calibrated verdicts (`SOUND` / `UNSOUND(#NN, …)` / `ABSTAIN`) instead of free-form analysis.

This is the plugin's adversarial-review convention. It is not an iron rule — orchestrators can skip a gate with a recorded `decision` journal entry naming the reason. The convention exists because single-critic reviews have a demonstrable false-SOUND rate on formal-verification artifacts, and asymmetric-vote aggregation across isolated critics catches classes of errors single reviewers miss.

## The six gates

| # | Gate | Lifecycle step | Workflow + insertion | Hook event |
|---|---|---|---|---|
| G0 | plan | post-ExitPlanMode, pre-workflow-resume | `navigate` Phase 1.5 post-plan-approval handoff | PostToolUse on ExitPlanMode (future; currently skill-driven) |
| G0b | plan-fidelity | post-workflow-resume, pre-first-substantive-action | `navigate` Phase 1 Step 2c, after `workflow_resumed` write, before `Skill(<target>)` | skill-driven (no hook); fires only when `pending_dispatch` originates from a G0 SOUND verdict |
| G1 | exploration | scope + blueprint | `build` after Phase 2, before Phase 3 | UserPromptSubmit + post-blueprint |
| G2 | per-layer modeling | each `.ivy` layer write | `build` Phase 3 | PostToolUse on `Write\|Edit` of `*.ivy` |
| G3 | test-spec | each test-spec write | `build` Phase 3 (test sub-step) | PostToolUse on `Write\|Edit` of `*_test_*.ivy` |
| G4 | verification | after `ivy_verify` returns | `verify` Phase 4 | PostToolUse on `ivy_verify` |
| G5 | trace analysis | after `ivy_iut_test` returns | `verify` Phase 5 | PostToolUse on `ivy_iut_test` |
| G6 | knowledge graduation | before persistence write | `knowledge-capture` Step 4c, before any Write to `.claude/rules/`, `MEMORY.md`, or `feedback_*.md` | skill-driven (no hook) |

## The four discipline contracts

These are the constraints that turn an MPE fan-out into an adversarial quality gate. The orchestrator (the workflow phase code or the wiring hook) is expected to honour all four; deviations should be recorded as a `decision` journal entry rather than silently accepted.

1. **Verbatim spawn prompts.** Load the per-gate critic prompt template from `references/critic_prompts/g{N}.md` (or `g0_plan.md`) and pass it to the `Agent` tool unmodified. Do not paraphrase, do not concatenate with chat history, do not synthesize an alternative. The first three paragraphs of every template are load-bearing — a session that rewrites them produces critics that grind and confidently get wrong answers.

2. **Dual context isolation.** Each critic sees only `(RFC clause(s) + the artifact + the catalog slice)`. It does not see the chat history, the design rationale, or sibling critics' verdicts. The orchestrator's spawn prompt is built from a single template render — no concatenation of upstream conversation.

3. **Asymmetric vote with pigeonhole exit.** Aggregate critic verdicts using the gate's tier configuration (see `model_tier_defaults.md`). Default Sonnet × 5 for G1–G5; G0's default is Opus × 3. Thresholds follow the same asymmetric discipline: `≥majority SOUND` → `VERDICT_SOUND`; `≥refute-threshold UNSOUND` → `VERDICT_UNSOUND`; otherwise → `VERDICT_ABSTAIN`. Stop spawning once a threshold is mathematically locked.

4. **Calibrated abstention as a structured verdict.** `VERDICT_ABSTAIN` is a first-class output, not a fallback to silence. It records which critics said what, why no threshold cleared, and a recommended next step (collect more evidence, consult user, or escalate to Opus).

## G0 — Plan-gate (pre-implementation plan audit)

Distinct from G1 (blueprint gate). G0 fires on plan artifacts — a plan file committing to design decisions that supersede prior `build-state.yaml` entries or propose new decisions the build workflow has not yet recorded.

**Trigger:**
- Journal entry `plan_approved` with a `plan_file` reference.
- Before any `workflow_resumed` entry for the same caller workflow.

**Scope:**
- The referenced plan file.
- Any RFC sections cited in the plan.
- The `build-state.yaml` decisions the plan supersedes (if listed via a `supersedes:` field in the journal entry or a `## Supersedes` section in the plan).
- The journal entries (`decision`, `gate_verdict`) that led to the superseded decisions.

**Critics:**
- Default tier: Opus × 3, confirmer-threshold 2, refute-threshold 1.
- Each critic independently reads the plan file, superseded decisions, and cited RFC sections — no shared context between critics.
- Verdict format: `SOUND` / `UNSOUND(#NN, …)` / `ABSTAIN`, matching G1–G5.

**Budget:**
- 3 G0 cycles per plan. After the third `UNSOUND`, escalate to the user for authority-override or plan revision. Cycle count lives in the `gate_verdict` payload's `cycle` field.

**Template:**
- `references/critic_prompts/g0_plan.md`

**Catalog slice:**
- `#100-149` (NCT base lifecycle — reused for scope-level audit)
- `#250-299` (migration/plugin-memory — plans often supersede decisions, which is a migration)
- Future slice `#050-099` reserved for plan-specific patterns (not yet populated)

**Output:**
- `gate_verdict` journal entry with `gate: "g0"` (matching the existing lowercase convention for `g1..g5`).

## G0b — Plan-fidelity (post-workflow-resume, pre-first-action)

Pairs with G0. G0 audits the plan file itself (is the plan sound?). G0b audits the agent's first substantive action after the plan clears (is the agent doing what the plan says?). Both fire post-ExitPlanMode; G0 fires at Phase 1.5 before the `pending_dispatch`; G0b fires at Phase 1 Step 2c after `workflow_resumed` is written and before `Skill(<target>)` is invoked.

**Trigger:**
- Phase 1 Step 2c has consumed a `pending_dispatch` entry.
- That `pending_dispatch` was emitted by Phase 1.5's G0 SOUND path — confirmed by a preceding `gate_verdict{gate: "g0", verdict: "SOUND"}` journal entry.
- No `gate_verdict{gate: "g0b"}` entry already exists paired against this `workflow_resumed`.

If the `pending_dispatch` did not originate from a G0 SOUND verdict (e.g., it is a normal workflow-to-workflow hand-off), G0b does NOT fire. This is a trigger condition, not a skip exception — non-plan-mode dispatches never qualify.

**Scope:**
- The approved plan file (path from the `plan_approved` entry).
- The `gate_verdict{gate: "g0", verdict: "SOUND"}` entry (authorization evidence).
- A description of the agent's first intended action: action type, target files, and phase label.

**Critics:**
- Default tier: Sonnet × 3, confirmer-threshold 2, refute-threshold 1.
- Each critic independently reads the plan file and the first-action description — no shared context between critics.
- Verdict format: `SOUND` / `UNSOUND(#0bNN, …)` / `ABSTAIN`.

**Budget:**
- 1 G0b cycle per plan execution. No re-run budget — G0b is a one-time pre-action check. On UNSOUND, the orchestrator halts, surfaces the deviation, and requires the user to decide (proceed with stated justification, revise the action, or re-enter plan mode).

**Template:**
- `references/critic_prompts/g0b_plan_fidelity.md`

**Catalog slice:**
- Inline (`#0b1-#0b5`, defined in the G0b critic prompt). No shared catalog slice — fidelity patterns are G0b-specific.

**Output:**
- `gate_verdict` journal entry with `gate: "g0b"`.

## G1 — Exploration (scope + blueprint)

See `references/critic_prompts/g1_exploration.md` for the verbatim template.

- **Trigger:** post-blueprint in `build` workflow.
- **Scope:** `build-state.yaml` + RFC scope notes.
- **Default tier:** Sonnet × 5, `≥4 SOUND` / `≥2 UNSOUND`.
- **Catalog slice:** `#100-149` + (`#150-199` if NACT) + `#250-299`.

## G2 — Per-layer modeling

See `references/critic_prompts/g2_modeling.md`.

- **Trigger:** each `.ivy` layer file write during `build` Phase 3.
- **Workflow filter:** fires only when `active-workflow.workflow == "build"`. Writes made during `verify` Phase 7 (fix) or `review` Phase 3 (resolution) do NOT dispatch G2 — see "G2/G3 workflow scope" below.
- **Scope:** the single just-written `.ivy` file.
- **Catalog slice:** `#200-249` + `#250-299` + (`#260-265` if NSCT).

## G3 — Test-spec

See `references/critic_prompts/g3_testspec.md`.

- **Trigger:** each `*_test_*.ivy` file write during `build` Phase 3 test sub-step.
- **Workflow filter:** fires only when `active-workflow.workflow == "build"`. Writes made outside `build` do NOT dispatch G3 — see "G2/G3 workflow scope" below.
- **Scope:** the test-spec file plus the requirement manifest and coverage matrix.
- **Catalog slice:** `#200-208` + `#256-259` + `#300-399`.

### G2/G3 workflow scope

Both gates are build-only by design. G2 audits layer modeling soundness during *construction* — ungrounded quantifiers, missing invariants, actions without require guards, the structural pathologies that matter most when a layer is being written for the first time. G3 audits test-spec soundness in the same construction window — coverage gaps against target RFC MUSTs, generator over-constraint, test pathologies that matter most at first authoring.

Why not fire during `verify` or `review`:

- Verify's Phase 7 fix loop is bounded by the journal-counted attempt cap (5 per test file, cumulative across sessions, soft-reset via `override_attempt_cap` decision). Counterexample-driven repairs rarely introduce the structural pathologies G2/G3 are calibrated for; broadening the gates raises audit volume faster than soundness confidence.
- Review's Phase 3 inline fixes are either small qualitative patches or, for structural concerns, dispatch back to `build` via `append_pending_dispatch(target_workflow="build", phase_hint="layer-check")`. Any `.ivy` write that warrants G2/G3 re-runs G2/G3 naturally when `build` re-enters Phase 3.

Re-engagement path when a user outside `build` wants an adversarial gate audit: emit `append_pending_dispatch(target_workflow="build", phase_hint="layer-check")` from the current workflow and clear the active-workflow flag. Navigate re-enters `build`, the next layer/test-spec edit fires the gate naturally.

## G4 — Verification

See `references/critic_prompts/g4_verification.md`.

- **Trigger:** after `ivy_verify` returns, during `verify` Phase 4.
- **Scope:** the `ivy_verify` JSON return + the verified spec.
- **Catalog slice:** `#200-249` + `#250-299` + `#400-499`.

## G5 — Trace analysis

See `references/critic_prompts/g5_trace.md`.

- **Trigger:** after `ivy_iut_test` returns, during `verify` Phase 5.
- **Scope:** IUT run artifacts (analysis JSON, Ivy trace, IUT log, pcap).
- **Catalog slice:** `#100-107` + `#500-559` + (`#560-589` if NSCT).

## G6 — Knowledge graduation

See `references/critic_prompts/g6_knowledge.md`.

- **Trigger:** before any `knowledge-capture` Step 4c write to `.claude/rules/`, `MEMORY.md`, or a `feedback_*.md` file. Fires on every candidate; there is no skip path.
- **Scope:** the candidate knowledge entry + the current content of the target file + the session digest grounding the candidate.
- **Default tier:** Sonnet × 3, `≥2 SOUND` / `≥2 UNSOUND`.
- **Catalog slice:** `#601-605` (knowledge-graduation patterns — defined in the G6 critic prompt).

## Tier configuration

`model_tier_defaults.md` holds the per-tier and per-gate critic counts and thresholds. The orchestrator reads `CLAUDE_MODEL_TIER` (`haiku` | `sonnet` | `opus`); if unset, defaults to Sonnet. G0 overrides the default to Opus × 3 regardless of `CLAUDE_MODEL_TIER`, because plan-artifact soundness has historically been the highest-value gate for Opus-tier review.

## Verdict persistence

Two event types in the workflow journal:

- **`gate_dispatched`** — written by the gate hook at the moment a gate is triggered, before any critic spawns. Breadcrumb lets the journal show which gates fired even if the orchestrator never dispatches the critics. Payload: `{gate, trigger, artifact?, layer?, methodology?, ...}`.

- **`gate_verdict`** — written by the orchestrator after the critic fan-out completes and the asymmetric vote has resolved. Payload schema:

```
ivy_workflow_state(
  action="append_journal",
  workflow=<active workflow>,
  phase=<gate insertion phase>,
  event_type="gate_verdict",
  payload={
    "gate": "g0" | "g0b" | "g1" | "g2" | "g3" | "g4" | "g5" | "g6",
    "verdict": "SOUND" | "UNSOUND" | "ABSTAIN",
    "vote": {"sound": int, "unsound": int, "abstain": int},
    "patterns": [{"id": "#NN", "file": "...", "line": int, "reason": "..."}],
    "abstain_reason": "..." | null,
    "tier": "haiku|sonnet|opus",
    "duration_s": float,
    "cycle": int  # G0: 1-3; G1–G5: typically 1 per build step
  }
)
```

Both event types appear alongside the existing `phase_transition`, `context_switch`, `error`, `decision`, `progress`, `session_start`, `session_end`, `plan_approved`, `workflow_resumed`. They are whitelisted in `_VALID_EVENT_TYPES` in both the local `workflow_state.py` helper and the MCP tool's `workflow_state.py` so writes are accepted.

## GAP marker convention

The `[GAP: #NN <reason>]` marker syntax, per-format placement rules (Ivy / YAML / Markdown / JSON), promotion lifecycle (to `RESOLVED`, `IUT_FINDING`, `DEFERRED`, `GUARD_ADDED`, `KNOWN_DEVIATION`, `N/A`), and anti-patterns live canonically in the rule `.claude/rules/gap-markers.md`. The gate discipline, verdict schema, and tier configuration below refer to that rule for marker semantics.

## Catalog

The `ivy-error-patterns` skill owns the numbered, append-only catalog (`verifier_patterns.md`). Sparse IDs preserve provenance; do not renumber. NACT entries (#150-199) load when `build-state.yaml:methodology` is `nact`; NSCT entries (#260-289 and #560-589) load when methodology is `nsct`.

Cross-skill access: each critic's verbatim spawn prompt instructs the critic to load the `ivy-error-patterns` skill via the Skill tool, which makes the catalog available. The critic then reads only entries in its assigned ID range. The spawning agent must have the Skill tool and `ivy-error-patterns` available — either through its `subagent_type` tool set or by declaring `skills: [ivy-error-patterns]` in the agent's frontmatter.
