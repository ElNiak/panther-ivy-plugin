# Harness Audit (Focused) — panther-ivy-plugin — 2026-04-29

Path: `…/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
Companion to: `.harness-audit/report-2026-04-29.md` (this morning's full four-pillar audit, 39 KB)
Audit lens: workflows, journalling/memory, subagent harness, plus two named Anthropic failure modes (context anxiety, self-evaluation problems)
Mode: read-only audit; this file is the only artifact produced.

## Context

This morning's full four-pillar audit (`report-2026-04-29.md`) covered context engineering, harness design, eval coverage, and prompting hygiene against the rubric in `~/.claude/skills/harness-audit/references/`. The user requested a second pass through three behavioral lenses the four-pillar template under-weights — workflows, journalling and memories maintenance, subagent harness — and explicit probing for two failure modes Anthropic has documented: **context anxiety** ("Some models exhibit 'context anxiety,' wrapping up work prematurely as they approach what they believe is their context limit") and **self-evaluation problems** (generator-evaluator collapse, asymmetric voting, shared-context confirmation bias).

This supplement does not duplicate the morning report. Where a morning finding is reconfirmed, it is referenced by check ID and not re-emitted. Where a finding is new since this morning or surfaces under a behavioral lens the four-pillar template did not exercise, it is reported here in full with severity, file:line, verbatim Anthropic quote, rationale, and either a unified-diff patch (in the Suggested Patches section) or a description-only recommendation.

## Summary

| Lens | Critical | Warning | Info |
|---|---:|---:|---:|
| 1. Workflows | 1 | 2 | 2 |
| 2. Journalling / memory | 1 | 2 | 1 |
| 3. Subagent harness | 1 | 3 | 1 |
| 4. Context anxiety | 1 | 0 | 3 |
| 5. Self-evaluations | 0 | 2 | 2 |
| **Phase-2 totals** | **4** | **9** | **9** |
| Phase-1 plugin-validator delta | 0 | 0 | 1 |
| Phase-1 skill-reviewer delta | 0 | 1 | 2 |
| Phase-1 claude-md-improver | n/a | n/a | n/a (no `CLAUDE.md` at plugin root) |
| **Combined totals** | **4** | **10** | **12** |

The four CRITICAL findings are all *named-reference drift*: a single class of bug (a string identifier in one file no longer matches a name registered elsewhere) appearing across four distinct surfaces. The morning audit caught the *workflow-name* drift on six runtime-fatal call sites; this audit adds three further drift surfaces the morning lens missed — a non-existent skill called from a Stop hook, a non-existent agent called from the meta workflow's three-loop, and a `.claude/rules/` rule that documents three agents that do not exist.

Top 4 critical findings (full detail below):

1. **`hooks/scripts/render-summary.py:253` calls non-existent skill** `panther-ivy-plugin:cross-cutting-knowledge-capture` on **every** Stop hook firing where `.ivy` files were modified. The skill never existed under that name; the actual session-end knowledge-capture path is the `g-knowledge-critic` agent dispatched 3× in parallel from the orchestrator. The same dead skill name also appears at `skills/verify-ops/references/glossary.md:11`. Quote: Q-A1 ("each could fail or be replaced independently") — the Stop hook is supposed to be an interface to a knowledge-capture component, but the component on the other end is missing.
2. **`skills/meta-self-mod-ops/SKILL.md:92` dispatches non-existent agent** `panther-ivy-plugin:model-reviewer`. The meta-agent's three-loop (implementer → spec-compliance review → plugin-conventions review) cannot execute the spec-compliance review step because no agent under that name exists in `agents/`. Plugin self-modification is therefore unrunnable as currently documented. Quote: Q-A1.
3. **`.claude/rules/agent-dispatch.md` (auto-loaded rule) references three non-existent agents** — `spec-analyst`, `model-reviewer`, `traceability-agent` — at lines 10, 27, 33, 37, 53, 54, 55, 56, 57, 65, 95, 106, 107, 115, 121, 124. The actual agents are `ivy-builder-agent`, `ivy-verifier-agent`, `ivy-reviewer-agent`. The same drift appears in `.claude/rules/ivy-formatting.md:47, 52, 54` (also auto-loaded). Both rules are injected into context every session via their `paths:` glob. Anthropic Q-A3: "those assumptions need to be frequently questioned because they can go stale as models improve" — the rules encode an old agent ontology.
4. **`hooks/scripts/render-summary.py:251–257` emits anxiety-inducing Stop-hook text** "Before ending this session, invoke …" — the framing the model sees on every turn-end where `.ivy` files were modified anthropomorphizes session pressure and is a documented context-anxiety induction pattern. Quote: Q-E1 ("Context, therefore, must be treated as a finite resource with diminishing marginal returns") — context is finite but the model should reason about it, not be pressured by language about ending.

## Phase 1 — refreshed reviewer findings (delta vs morning)

### `plugin-dev:plugin-validator` (delta)

No CRITICAL or WARNING deltas since this morning. One INFO addition:

- **INFO** `commands/README.md:5` — claims "7 shortcut commands" and additionally documents `/set-workspace` and `/clear-workspace`; only `nct-health.md` and `nct-iut-test.md` exist on disk. Same root cause as the morning's `/set-workspace`-references finding, surfacing in a new file.

The morning's CRITICAL workflow-name drift has uncommitted in-flight edits at five of six call sites. Unfinished. Severity stays CRITICAL until commit + a fresh grep returns clean.

### `plugin-dev:skill-reviewer` (delta)

- **WARNING (NEW)** `skills/ivy-syntax/SKILL.md:47` references `ivy-error-patterns` — a skill that does not exist anywhere in the plugin. Morning audit's CRITICAL #1 catalogued six dead `Skill()` references but missed this seventh one. Fix: rewrite to "load the `verification-failures` skill (`references/debugging-methodology.md`)".
- **INFO** `skills/ivy-toolkit/references/tool-catalog.md:429` now has a `<!-- TODO(harness-audit 2026-04-29): … -->` comment block above the two dead `Skill()` invocations on line 435. The TODO signals awareness without fixing — the live calls still execute and still fail. Pick one of the three options the TODO enumerates (restore, redirect, delete) and remove the TODO.
- **INFO** `commands/nct-health.md:24` shows the morning's Patch 3 (caller-side return cap "Return under 800 words; JSON output per `<output_schema>`") applied for one call site. Extend to the four other dispatchers (`build-ops`, `ivy`, `meta-self-mod-ops`, `review-ops`, `verify-ops`).

No remediation has landed in the tree since morning; in-flight edits exist but are uncommitted. Patches 1, 2, 4–6 from the morning audit remain unapplied.

### `claude-md-management:claude-md-improver`

Skipped. No `CLAUDE.md` at plugin root. Plugin metadata is otherwise covered by `.claude-plugin/plugin.json` (57 lines) and `README.md` (252 lines). Not a finding.

---

## Lens 1 — Workflows

### W1 — Test/production schema drift on workflow names — **WARNING**

`tests/test_workflow_state.py:155` declares `_KNOWN = {"workflow-navigate", "workflow-build", "workflow-verify", "workflow-review", "workflow-triage"}` — the **old** prefixed schema. Production `hooks/scripts/workflow_state.py:268–275` declares `_KNOWN_WORKFLOWS = frozenset({"navigate", "build", "verify", "review", "triage", "meta"})` — the **new** unprefixed schema. The migration script `scripts/migrate-active-workflow.sh` was added in CHANGELOG v0.11.0 to rewrite `.panther-ivy/active-workflow` files from prefixed to unprefixed. Tests use the prefixed names in `mod.set_active_workflow(str(tmp_path), "workflow-verify", "init")` calls (lines 34, 47, 61, 75, 88, 164, 195, 207, 285, 300, 311, 334, 343, 353, 354, 361, 363, 367), so either:

- (a) tests pass against a `validate_active_workflow` that silently accepts unknown names (a backward-compat shim), or
- (b) tests assert behaviour that the production code no longer exhibits — the test suite gives a green light to a stale invariant.

Either way, the test suite is no longer asserting what the runtime enforces. Per `feedback_no_backward_compat_shims`, (a) is also a violation if it exists. Fix: rewrite tests to use unprefixed names. (Patch 8 below.) Quote: Q-A3 "those assumptions need to be frequently questioned because they can go stale as models improve" — `https://www.anthropic.com/engineering/managed-agents`.

### W2 — Journal writes are race-free — **INFO** (PASS)

Inspected `hooks/scripts/workflow_state.py::append_journal_event()` and the eight PostToolUse + Stop + SessionEnd hook scripts. Journal writes happen only on hook boundaries (PostToolUse, Stop, SessionEnd). No mid-tool race observed. The strict ordering contract in `.claude/rules/postuse-hook-ordering.md` ensures `post-write-workflow-aware.py` (statusline + orientation hint) runs before `assess-modeling.py`/`assess-testspec.py`/`assess-trace.py` (gate dispatchers) without state contention.

### W3 — `_KNOWN_WORKFLOWS` includes a self-documented "navigate" name — **INFO** (deliberate)

`workflow_state.py:268–275` keeps `"navigate"` in `_KNOWN_WORKFLOWS` even though no workflow specialist agent owns `navigate` (the orchestrator is named `ivy`). The header comment on lines 265–267 documents this intentionally: "specialised ops-skills (skills/{build,verify,review,triage,meta}-ops plus the navigate flow inside the orchestrator) are the authoritative writers, all using the unprefixed names below." `navigate` is the orchestrator's own internal flow name, not a missing workflow. Not a finding; flagged for visibility because `render-summary.py:221` has `elif workflow == "navigate":` and the casual reader would interpret that as orphan code.

### W4 — `.panther-ivy/observability/` JSONL retention is unbounded — **WARNING**

The observability log under `.panther-ivy/observability/` (written by `hooks/scripts/observability/observe.py` on every PreToolUse, PostToolUse, SessionStart, SessionEnd, Stop, SubagentStart, SubagentStop, PreCompact, UserPromptSubmit, Notification, PermissionRequest, PostToolUseFailure event) has no retention policy in `workflow_state.py` or in any Stop/SessionEnd hook. `hooks/scripts/detect-ivy-workspace.sh:83` does `find ${IVY_WORKSPACE_ROOT}/.observability/sessions -mtime +7 -maxdepth 1 -type d -exec rm -rf {} \;` for the workspace-root observability directory, but the protocol-scoped `.panther-ivy/observability/` directory is never pruned. Long-running protocol workflows accumulate JSONL indefinitely. Description-only fix below.

### W5 — `.backup/` is in-tree and deliberate — **INFO**

`.backup/skills-restructure-2026-04-27/`, `.backup/skills-merged-2026-04-27/`, `.backup/2026-04-28/` — three dated backup directories from Phase B/C/D refactor checkpoints. Per user feedback memory `feedback_no_relocate_backup_files` (in `~/.claude/projects/.../memory/`), this audit explicitly does **not** propose relocating, archiving, or deleting these directories. Flagged here only so the morning report's relocation suggestion is explicitly contested. Default policy is leave-alone.

---

## Lens 2 — Journalling and memory maintenance

### J1 — Stop hook is anxiety-inducing AND calls a non-existent skill — **CRITICAL**

`hooks/scripts/render-summary.py:251–257` emits, on every Stop where `.ivy` files were modified:

```python
parts.append(
    "[KNOWLEDGE GATE] Before ending this session, invoke "
    'Skill(skill="panther-ivy-plugin:cross-cutting-knowledge-capture") to capture '
    "any learnings from this session. If no learnable patterns are "
    "found, the skill exits silently."
)
```

Two distinct failures:

1. The skill `panther-ivy-plugin:cross-cutting-knowledge-capture` does not exist. `ls plugins/panther-ivy-plugin/skills/` returns `apt-attack-patterns, build-ops, ivy, ivy-syntax, ivy-toolkit, meta-self-mod-ops, methodology, propagation-patterns, review-ops, specification-patterns, triage-ops, verification-failures, verify-ops` — no skill under any prefix matches. Same dead reference at `skills/verify-ops/references/glossary.md:11`.
2. "Before ending this session, invoke …" is a documented context-anxiety induction pattern. Anthropic on managed agents (URL: `https://www.anthropic.com/engineering/managed-agents`): "Some models also exhibit 'context anxiety,' in which they begin wrapping up work prematurely as they approach what they believe is their context limit." Stop-hook prompts that frame work in terms of session-end pressure can amplify that bias. Cross-references the C2 finding under Lens 4.

The actual session-end knowledge-capture mechanism is the `g-knowledge-critic` agent dispatched 3× in parallel from the orchestrator (per `agents/g-knowledge-critic.md` and `skills/ivy/references/parallel-dispatch.md`) — not a skill.

Fix: Patch 1 below (rewrite the message to dispatch the agent and remove the anxiety phrasing). Quote: Q-A1 "each could fail or be replaced independently" — the Stop hook's message points at a missing component.

### J2 — `.claude/rules/insights.md` is a deliberate placeholder — **INFO**

The file is 7 lines:

```
---
paths: ["**/*.ivy"]
---

## Emergent Insights

Uncategorized learnings that may graduate to a primary category when 3+ entries cluster around the same theme.
```

Per user feedback `feedback_keep_insights_placeholder`, this is intentional graduation slot — not a stub to delete. Flagged for visibility.

### J3 — `clean=True` is hardcoded in `record-session-end.py` — **WARNING**

`hooks/scripts/record-session-end.py:32` always sets `clean = True` before writing the `session_end` event. The field has no source of truth — there is no detection of unclean exits (Z3 timeouts, MCP disconnects, raised errors). Hard exits (Ctrl-C, harness crash, OOM) bypass the Stop hook entirely and never reach this code at all, so `clean=True` from this hook means "Stop hook fired and reached line 33" — a tautology. The field is meaningless as written. Description-only recommendation below: either remove `clean` from the schema, or add a SessionEnd-side sweeper that detects sessions without a `session_end` event and writes `clean=False` retroactively.

### J4 — G6 knowledge-capture dispatch is lazy, not eager — **WARNING**

`hooks/scripts/record-session-end.py` writes `session_end` and rotates the journal but does **not** dispatch the `g-knowledge-critic` agent. The agent is supposed to fire 3× in parallel "at session-end" per its description (`agents/g-knowledge-critic.md:3`). The actual dispatch path is: orchestrator detects the `session_end` event in the journal on the *next* turn (Phase 1.5 of `skills/ivy/SKILL.md`), then issues `pending_dispatch(workflow="navigate", reason="post-session G6 required")` which routes the user on the *turn after that*.

This requires (i) the user starts a follow-up turn and (ii) the orchestrator reads the journal first thing. Hard exits (Ctrl-C, crash, no follow-up turn) drop the candidate learnings entirely. Quote: Q-A6 "Nothing in the harness needs to survive a crash. When one fails, a new one can be rebooted" — the design correctly assumes hard-exit recovery, but the recovery path here is "depend on the user coming back," which is weaker than the article's pattern. Description-only recommendation: dispatch G6 inline inside the Stop hook (or move it to SessionEnd, which fires on harness shutdown), so candidate learnings are evaluated before the journal rotates and the candidate context is gone.

---

## Lens 3 — Subagent harness

### H1 — Specialist agents have clean dispatch contracts — **INFO** (PASS)

All five specialists (`ivy-builder-agent`, `ivy-verifier-agent`, `ivy-reviewer-agent`, `ivy-triage-agent`, `ivy-meta-agent`) declare `<role>`, `<dispatch-context>` (with required and optional fields per `.claude/rules/agent-dispatch.md` schema), `<output_schema>` (5-field JSON capped at ≤800 words: `claim`, `evidence_paths`, `gate_status`, `next_dispatch_hint`, `tool_invocations`), `tools:` allowlist, and `forbidden_tools:` (where applicable). Quote: Q-E8 "Specialized sub-agents can handle focused tasks with clean context windows" — the contracts cleanly separate dispatch concerns.

### H2 — `forbidden_tools` enforced as expected — **INFO** (PASS)

| Agent | Forbidden tools | Rationale |
|---|---|---|
| `ivy-builder-agent` | `Bash` | prevents shell escape during code generation |
| `ivy-verifier-agent` | `Edit`, `Write` | read-only on specs; enforces verifier ≠ builder |
| `ivy-reviewer-agent` | `Edit`, `Write`, `Bash` | pure analysis; zero side effects |
| `ivy-triage-agent` | `Edit`, `Write` | health check only |
| `ivy-meta-agent` | `[]` (none) | only agent allowed to mutate plugin source |
| Critics (g-plan, g-fidelity, g-knowledge) | `[]` (read-only via `Read`/`Grep`/`Glob` only) | no write capability |

### H3 — Caller-side return-size cap missing on 4 of 5 dispatching skills — **WARNING**

Reconfirmed from morning audit. `commands/nct-health.md:24` has been updated with "Return under 800 words; JSON output per `<output_schema>`". Four other dispatchers still lack the caller-side cap: `skills/build-ops/SKILL.md`, `skills/ivy/SKILL.md`, `skills/meta-self-mod-ops/SKILL.md`, `skills/review-ops/SKILL.md`, `skills/verify-ops/SKILL.md`. Agent-side `<output_schema>` declares ≤800 words but Anthropic's pattern requires both sides. Quote: Q-E9 "Returns only a condensed, distilled summary of its work, often 1,000-2,000 tokens" — `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`. Patch 3 below.

### H4 — Tool counts within budget — **INFO** (PASS)

| Agent | Tool count |
|---|---:|
| `ivy-builder-agent` | 11 |
| `ivy-verifier-agent` | 10 |
| `ivy-reviewer-agent` | 10 |
| `ivy-triage-agent` | 10 |
| `ivy-meta-agent` | 7 |
| `g-plan-critic` | 3 |
| `g-fidelity-critic` | 3 |
| `g-knowledge-critic` | 3 |

Maximum 11; threshold is 15. Pass.

### H5 — Builder agent has explicit self-evaluation responsibility — **WARNING**

`agents/ivy-builder-agent.md:28` instructs the builder: "You hold post-build review responsibility for newly written layers — invariant quality, type safety, isolation-size compliance, and structural correctness — before handing off to the verifier."

This is a generator-evaluator overlap. The builder writes the spec, then is told to grade it on four dimensions before the verifier sees it. Quote: Q-C3 ("Agents evaluating their own work respond by confidently praising the work — even when…the quality is obviously mediocre", `https://www.anthropic.com/engineering/harness-design-long-running-apps`).

The mitigation is downstream — the verifier (with `ivy_verify`/`ivy_compile`/Z3-grounded mechanical checks) and reviewer (with `ivy_rfc`-grounded RFC checks) are independent generator-evaluator triangles. But in the dispatch chain Builder → Verifier → Reviewer, the Builder's self-grade is the first signal the orchestrator sees, and a "SOUND" verdict from the builder's self-review may bias subsequent dispatch decisions.

Fix: weaken the builder's self-review responsibility from "post-build review" (a verdict) to "pre-handoff sanity check" (an internal smoke test, not a grade). Patch 4 below.

### H6 — Critic preconditions are documented in agent headers but not enforced — **INFO**

Each `g-*-critic` agent header documents its dispatch trigger (post-plan-approved, first-action-post-G0-SOUND, session-end). The actual trigger logic lives in `skills/ivy/SKILL.md` routing and the orchestrator's parallel-dispatch helper (`skills/ivy/references/parallel-dispatch.md`). Critics themselves apply only the calibrated `ABSTAIN` discipline as a precondition check — they vote ABSTAIN if context is missing rather than refusing to participate. This is **correct** per Anthropic's adversarial-vote pattern, but it relies on the orchestrator's correctness — there is no critic-side check that says "this dispatch is the wrong moment for me." Not a finding; flagged for awareness.

### H7 — Meta agent self-audits its own writes (mitigated) — **INFO**

`agents/ivy-meta-agent.md:20` describes the meta agent self-auditing its diff against `skill-conventions.md`, the three-layer split, plugin self-containment, and references discipline before returning. This is generator-evaluator overlap on its face, but the mitigation is in `skills/meta-self-mod-ops/SKILL.md` Phase 2: the meta agent dispatches a three-loop (implementer → spec-compliance review → plugin-conventions review), and only ships when all three return SOUND. The "self-audit" in agent body line 20 refers to the meta agent **supervising its own three-loop**, not Claude grading its own diff directly. Pass — but see H8 below: the three-loop is currently broken because two of the reviewer agents it dispatches do not exist.

### H8 — Three non-existent agents referenced across rules and one workflow — **CRITICAL**

The auto-loaded rule `.claude/rules/agent-dispatch.md` (paths glob: `**/*.md`, injected this session per system-reminder) names three "specialist agents" that the actual `agents/` directory does not contain:

| Referenced as | Actual agent |
|---|---|
| `spec-analyst` | `ivy-verifier-agent` (closest functional match) |
| `model-reviewer` | `ivy-reviewer-agent` (closest functional match) |
| `traceability-agent` | `ivy-reviewer-agent` (handles `rfc_source`/`existing_manifest` per its frontmatter) |

The rule references the dead names at lines 10, 27, 33, 37, 53, 54, 55, 56, 57, 65, 95, 106, 107, 115, 121, 124. The same dead names appear in `.claude/rules/ivy-formatting.md` (also auto-loaded) at lines 47, 52, 54, in `evals/workflow_dispatch_eval.json:175` ("update agents/spec-analyst.md frontmatter…"), and in `skills/meta-self-mod-ops/SKILL.md:92`:

```
Agent(subagent_type="panther-ivy-plugin:model-reviewer",
      description="Spec-compliance review of <task>",
      prompt="<diff + original spec + acceptance criteria>")
```

This is **runtime-fatal** for the meta workflow. The plugin's three-loop self-modification cycle cannot complete because the spec-compliance review step dispatches a non-existent agent. The plugin-conventions review at the next step (Phase 2 Step 3) presumably has the same issue.

Quote: Q-A1 "Each became an interface that made few assumptions about the others, and each could fail or be replaced independently" — `https://www.anthropic.com/engineering/managed-agents`. The agent layer was renamed in a refactor; the rule layer was not.

Fix: this is a multi-file rewrite. See Patch 2 (point fix for `meta-self-mod-ops:92`) and Description-only Recommendation D1 (rule-wide rename).

---

## Lens 4 — Context anxiety

### C1 — Three context-anxiety language hits — **INFO** (mostly)

```
agents/g-knowledge-critic.md:3        "session is wrapping up; orchestrator about to fire G6"
hooks/scripts/render-summary.py:253   "Before ending this session, invoke …"      ← CRITICAL (see C2)
skills/build-ops/references/phase-5-quality-gate.md:58
                                       "Run full verification before wrapping up"
```

The first is example phrasing inside the agent description (a contextual marker for when the orchestrator dispatches G6, not a runtime prompt). The third in build-ops phase-5 frames a quality gate as session-end activity rather than phase-end activity, which is a mild anxiety inducer — recommendation: rewrite to "Run full verification at the end of this build phase, before transitioning to the next phase" (description-only). The second is the load-bearing hit, escalated to C2.

### C2 — Stop hook prints anxiety language on every fire — **CRITICAL**

Already detailed under J1. The Stop hook output `[KNOWLEDGE GATE] Before ending this session, invoke …` lands in the agent's context on every turn-end. The phrasing pressures the model to wrap up rather than to reason about whether further work is needed. The fix is in Patch 1.

Quote: Q-E1 "Context, therefore, must be treated as a finite resource with diminishing marginal returns" — `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`. Context is finite; that does not mean prompts should anthropomorphize the boundary.

### C3 — PreCompact / SessionEnd hooks are clean — **INFO** (PASS)

`hooks.json` PreCompact: only `observability/observe.py` runs (silent JSONL capture, no messages). SessionEnd: `cleanup-ivy-lsp.sh` (LSP teardown, no messages) plus `observability/observe.py`. No anxiety language. Pass.

### C4 — Memory-write rules are not anxiety-inducing — **INFO** (PASS)

Reviewed `.claude/rules/iron-laws.md`, `agent-dispatch.md`, `mcp-tool-reliability.md`, `postuse-hook-ordering.md`, `ivy-formatting.md`, `output-style.md`, `nct-methodology.md`, `plan-mode.md`, `skill-conventions.md`. None contain "if context is low, save and stop" or equivalent. Pass.

### C5 — No counter-messaging present — **INFO**

The plugin contains no explicit anti-anxiety prompts of the form "you have a 1M context window; do not stop work prematurely; large tasks are expected to span many turns." Quote: Q-A3 "those assumptions need to be frequently questioned because they can go stale as models improve" — when a plugin both fires anxiety language (C2) and lacks counter-messaging, the imbalance compounds. Description-only recommendation D2 below: add a single short counter-prompt to the orchestrator's Phase 1 system reminder.

---

## Lens 5 — Self-evaluations (empirical + adversarial)

### 5a — Gate-critic prompts are calibrated — **INFO** (PASS)

Read `agents/g-plan-critic.md`, `agents/g-fidelity-critic.md`, `agents/g-knowledge-critic.md` in full. Each declares the rubric `VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN` per the gate-verdict severity system in `.claude/rules/ivy-formatting.md`. Each agent body has an explicit "Calibrated Abstention" section instructing the critic to vote ABSTAIN rather than collapse to SOUND when evidence is missing:

> g-knowledge-critic.md:46: "ABSTAIN is first-class per `ivy-formatting.md` severity-system 2; do not collapse to SOUND-by-default when evidence is missing."

The phrasing is a direct counter to the bias Q-C3 documents ("Agents evaluating their own work respond by confidently praising the work"). Pass.

### 5b — Empirical verdict-distribution check — **INSUFFICIENT_DATA**

The plan called for grepping `gate_verdict` events in `.panther-ivy/journal-archive/` and counting SOUND : UNSOUND : ABSTAIN ratios per gate. In this worktree, `.panther-ivy/` does **not exist** at any path under the plugin tree. A broader search across `**/*.yaml` and `**/*.jsonl` for `gate_verdict|VERDICT_SOUND|VERDICT_UNSOUND` returns no results outside test fixtures and the `.harness-audit/` reports. The check returns `INSUFFICIENT_DATA`. To exercise this check, a workflow run is required first; a follow-up audit after a representative protocol session can re-grade.

### 5c — Adversarial design probe — **PROBE FAILED TO FALSIFY**

Hypothetical: a builder writes `quic_X.ivy` that compiles cleanly but encodes a subtle invariant violation. Verifier dispatched with `failure_context = "ivy_verify SOUND"`. Reviewer dispatched with the same `target_files`. Both read the same workspace, both see the same `ivy_compile` output. Question: does any agent in the current dispatch chain receive an *independent* counter-source (RFC text, prior-verified reference spec, golden trace) that would surface the violation?

**Answer: yes.**

- The reviewer agent (`agents/ivy-reviewer-agent.md:14–18`) has the `ivy_rfc` MCP tool in its allowlist. The reviewer can fetch RFC normative text directly from the rfc subsystem and compare it against the spec's bracket tags, independently of whatever the builder wrote.
- The verifier agent (`agents/ivy-verifier-agent.md:12–16`) has `ivy_verify`, `ivy_compile`, `ivy_iut_test` — all three return Z3-grounded or wire-protocol-grounded results that are independent of the prose in the builder's spec. A subtle invariant violation either makes Z3 return a counterexample or makes the IUT trace mismatch the spec's send/recv sequence, both of which surface independently.

The probe **fails to falsify** the design as long as the reviewer actually invokes `ivy_rfc` and the verifier actually runs `ivy_verify`. The dispatch context does **not require** either of those tool invocations — the agents are trusted to choose their tool path. So the design is robust *conditional on agent self-discipline*, not by structure. Description-only recommendation D3: add a "Tool requirement" line to each specialist's `<dispatch-context>` mandating which tool calls are required to render a verdict, and have the orchestrator reject the agent's return if the `tool_invocations` count in the JSON output schema is zero.

### 5d — Voting-rule arithmetic — **WARNING**

`skills/ivy/references/parallel-dispatch.md:19–24` aggregation rule:

| Distribution | Outcome |
|---|---|
| 3 SOUND | proceed |
| 2 SOUND, 1 ABSTAIN | proceed |
| 2 SOUND, 1 UNSOUND | ABSTAIN; the dissent must be reconciled before proceeding |
| 1 SOUND, 1 UNSOUND, 1 ABSTAIN | ABSTAIN; reconcile |
| 3 ABSTAIN | re-dispatch with broader evidence |
| ≥ 2 UNSOUND | halt; surface to user via `AskUserQuestion` |

Mathematically symmetric in favour of dissent — a single UNSOUND voice vetoes the proceed path by forcing an ABSTAIN-reconcile. This is sound aggregation. Quote: Q-D4 "Two domain experts would independently reach the same pass/fail verdict" — the rule respects this when independence holds.

The finding is procedural: the rule says "the dissent must be reconciled" but does not specify the reconciliation procedure. Reconciliation could be (a) re-read the artefact and re-dispatch, (b) populate `prior_findings` with the UNSOUND citation and re-dispatch, or (c) the orchestrator overrules the UNSOUND inline ("I read the dissent, decided it's wrong, proceed"). Option (c) is exactly the bias Q-C3 documents. The rule has no language preventing (c).

Fix: add a sentence to `parallel-dispatch.md` requiring re-dispatch (not orchestrator override) as the only reconciliation path. Patch 5 below.

---

## Suggested Patches

Each patch is a unified diff ready to apply with `git apply`. They are advisory — this audit is read-only. Apply only after review.

### Patch 1 — render-summary.py: dispatch G6 critic, remove anxiety phrasing — **CRITICAL (J1, C2)**

```diff
--- a/hooks/scripts/render-summary.py
+++ b/hooks/scripts/render-summary.py
@@ -249,12 +249,12 @@ def build_summary(
             warning_lines = ["[JOURNAL AUDIT]"] + [f"  - {w}" for w in audit_warnings]
             parts.append("\n".join(warning_lines))
 
-    # Knowledge gate prompt
+    # Knowledge gate hint (G6 dispatch via the orchestrator's parallel-dispatch helper)
     parts.append(
-        "[KNOWLEDGE GATE] Before ending this session, invoke "
-        'Skill(skill="panther-ivy-plugin:cross-cutting-knowledge-capture") to capture '
-        "any learnings from this session. If no learnable patterns are "
-        "found, the skill exits silently."
+        "[KNOWLEDGE GATE] If this session surfaced new patterns, fix strategies, "
+        'or surprising verdicts, dispatch g-knowledge-critic 3x in parallel '
+        '(see skills/ivy/references/parallel-dispatch.md) to vote on whether to '
+        "persist learnings. The critic returns ABSTAIN when no candidates are present."
     )
 
     return "\n".join(parts)
```

### Patch 2 — meta-self-mod-ops: rename `model-reviewer` to `ivy-reviewer-agent` — **CRITICAL (H8)**

```diff
--- a/skills/meta-self-mod-ops/SKILL.md
+++ b/skills/meta-self-mod-ops/SKILL.md
@@ -89,7 +89,7 @@ Dispatch the existing `model-reviewer` agent with `review_scope="spec-compliance
 Returns SOUND / UNSOUND(#NN, reason, file:line) / ABSTAIN per the gate-verdict severity system in `.claude/rules/ivy-formatting.md`.
 
 ```
-Agent(subagent_type="panther-ivy-plugin:model-reviewer",
+Agent(subagent_type="panther-ivy-plugin:ivy-reviewer-agent",
       description="Spec-compliance review of <task>",
       prompt="<diff + original spec + acceptance criteria>")
 ```
```

The same renaming should be applied to Step 3 (plugin-conventions review) further down in the file. The exact line is not in the snippet I read; locate it during application.

### Patch 3 — verify-ops/glossary.md: replace dead skill reference — **CRITICAL (J1, secondary site)**

```diff
--- a/skills/verify-ops/references/glossary.md
+++ b/skills/verify-ops/references/glossary.md
@@ -8,7 +8,7 @@
 | Term | Definition |
 |---|---|
-| Knowledge gate | A phase-boundary checkpoint that loads `cross-cutting-knowledge-capture` to surface session learnings worth persisting (rules, references, feedback). Knowledge gates fire after Phase 4 (verify) and before workflow-completion. |
+| Knowledge gate | A phase-boundary checkpoint that dispatches the `g-knowledge-critic` agent (3x in parallel) to vote on whether session learnings should persist (rules, references, feedback). Knowledge gates fire after Phase 4 (verify) and before workflow-completion. |
```

### Patch 4 — ivy-builder-agent: weaken self-review language — **WARNING (H5)**

```diff
--- a/agents/ivy-builder-agent.md
+++ b/agents/ivy-builder-agent.md
@@ -25,7 +25,7 @@ skills:
 ---
 
 <role>
-You are the panther-ivy-plugin build specialist. You construct and extend Ivy formal protocol models following the 14-layer NCT template, the NACT 6-stage attack template, and the NSCT simulation template. You scaffold new layers, write Ivy 1.7 specifications grounded in RFC normative text, and propagate field/variant changes through stack/entities/shims/utils with type-safe edits. You hold post-build review responsibility for newly written layers — invariant quality, type safety, isolation-size compliance, and structural correctness — before handing off to the verifier. Dispatched by the panther-ivy-plugin ivy orchestrator skill when the user requests model authoring, layer scaffolding, or coordinated multi-file propagation.
+You are the panther-ivy-plugin build specialist. You construct and extend Ivy formal protocol models following the 14-layer NCT template, the NACT 6-stage attack template, and the NSCT simulation template. You scaffold new layers, write Ivy 1.7 specifications grounded in RFC normative text, and propagate field/variant changes through stack/entities/shims/utils with type-safe edits. You run a sanity check (parses, includes resolve, no obvious syntax errors) before returning, then hand off to the verifier for invariant quality, type safety, isolation-size compliance, and structural-correctness verdicts; the verifier — not the builder — is the authority on those four dimensions. Dispatched by the panther-ivy-plugin ivy orchestrator skill when the user requests model authoring, layer scaffolding, or coordinated multi-file propagation.
 </role>
```

### Patch 5 — parallel-dispatch.md: forbid orchestrator override on dissent — **WARNING (5d)**

```diff
--- a/skills/ivy/references/parallel-dispatch.md
+++ b/skills/ivy/references/parallel-dispatch.md
@@ -22,6 +22,11 @@ Read the three verdicts. The vote is asymmetric: a single UNSOUND citing concret
 - ≥2 ABSTAIN → ABSTAIN; gather more evidence (re-read the artefact, broaden include closure, populate `prior_findings`) and re-dispatch.
 - Any other distribution (notably 2 SOUND + 1 UNSOUND, 1 SOUND + 1 UNSOUND + 1 ABSTAIN, etc.) → ABSTAIN; the dissent must be reconciled before proceeding.
 
+**Reconciliation procedure (binding).** Reconciliation means re-dispatch with the dissenting critic's `prior_findings` populated and the artefact re-read; it does NOT mean the orchestrator overrules the UNSOUND inline. Inline override is the bias Anthropic documents in *Harness Design for Long-Running Apps* (https://www.anthropic.com/engineering/harness-design-long-running-apps): "Agents evaluating their own work respond by confidently praising the work." If after one re-dispatch the dissent persists with new evidence, surface to the user via `AskUserQuestion` (proceed-with-rationale, abandon, retry-with-broader-context).
+
 ## Verbatim critic prompt requirement
```

### Patch 6 — Caller-side return cap on the four remaining dispatchers — **WARNING (H3)**

The morning's CRITICAL #3 is reconfirmed. Apply the `commands/nct-health.md:24` pattern ("Return under 800 words; JSON output per `<output_schema>`.") to the dispatching skills:

- `skills/build-ops/SKILL.md` — every `Agent(subagent_type=...)` invocation prompt
- `skills/ivy/SKILL.md` — orchestrator dispatches
- `skills/review-ops/SKILL.md` — every `Agent(...)` invocation
- `skills/verify-ops/SKILL.md` — every `Agent(...)` invocation
- `skills/meta-self-mod-ops/SKILL.md` — every `Agent(...)` invocation (after Patch 2 lands)

Diffs deferred to follow-up — the morning report's Patch 3 already covers the structural shape of the change; this audit reconfirms the scope is unchanged. Quote: Q-E9 "Returns only a condensed, distilled summary of its work, often 1,000-2,000 tokens".

### Patch 7 — Test schema: rename to unprefixed names — **WARNING (W1)**

`tests/test_workflow_state.py` and `tests/test_style_utils.py` and `tests/test_compose_style.py` use the OLD `workflow-*` prefixed schema. The morning audit's CRITICAL #1 was about source-tree drift; this audit adds the test-tree drift as a sibling problem. The diff is mechanical and large (every `set_active_workflow(..., "workflow-verify", …)` becomes `set_active_workflow(..., "verify", …)` etc.). Apply via `sed -i 's/"workflow-\(navigate\|build\|verify\|review\|triage\)"/"\1"/g' tests/test_workflow_state.py tests/test_style_utils.py tests/test_compose_style.py` followed by `pytest tests/` to confirm every assertion still holds against the unprefixed runtime.

After application, also update `tests/test_workflow_state.py:155` from `_KNOWN = {"workflow-navigate", "workflow-build", "workflow-verify", "workflow-review", "workflow-triage"}` to `_KNOWN = {"navigate", "build", "verify", "review", "triage", "meta"}`. Note that the production set has six entries; the test set has only five (missing `meta`) — flag this as a sub-finding when applying.

---

## Description-only recommendations

These findings need human judgement to fix correctly. No mechanical diff is offered.

### D1 — Rename three dead specialist agents in two auto-loaded rules — **CRITICAL (H8)**

`.claude/rules/agent-dispatch.md` and `.claude/rules/ivy-formatting.md` reference `spec-analyst` (→ `ivy-verifier-agent`), `model-reviewer` (→ `ivy-reviewer-agent`), and `traceability-agent` (→ `ivy-reviewer-agent`). The semantic mapping is best done by the meta agent itself — not by a `sed` rename — because some references describe behaviour that does not 1:1 map (e.g. `traceability-agent` extraction mode is now the reviewer agent's `existing_manifest` field; `spec-analyst` verification mode is now the verifier agent's `failure_context` field). Dispatch the meta agent with task: "rename three dead agent names across two .claude/rules/ files; preserve behavioural intent in each occurrence; emit a single commit." Acceptance: a fresh `grep -nE 'spec-analyst|model-reviewer|traceability-agent' .claude/rules/` returns empty.

### D2 — Add anti-anxiety counter-messaging — **INFO (C5)**

The orchestrator's `skills/ivy/SKILL.md` Phase 1 (the silent context scan) is the right place to inject one short counter-prompt. Suggested wording: "You are operating with a 1M-token context. Long tasks are expected to span many turns. Do not abridge work or wrap up early because you sense the context is filling — the harness will compact older context as needed. Continue until the task is complete or the user redirects."

### D3 — Mandate tool invocation in dispatch context — **WARNING (5c)**

Add a `<field name="required_tool_invocations" required="true">` to each specialist agent's `<dispatch-context>` declaring which MCP tools must be invoked at least once for a verdict to be valid. Reviewer: `ivy_rfc` + `ivy_coverage`. Verifier: `ivy_verify` or `ivy_compile`. The orchestrator rejects returns where `tool_invocations` (from the agent's output schema) is zero or where the required tools were not in the call set. Quote: Q-E3 "Tools should be self-contained, robust to error, and extremely clear with respect to their intended use" — making tool invocation part of the contract makes the behaviour clear.

### D4 — Eager G6 dispatch from Stop hook — **WARNING (J4)**

Move the `g-knowledge-critic` 3x parallel dispatch from "next-turn lazy detection" to "inline in `record-session-end.py`" or "inline in a SessionEnd hook". The trade-off: inline dispatch costs Stop-hook latency (3 critic invocations × ~30s each = ~90s, exceeds Stop's 5s timeout). Mitigation: dispatch in background with `Agent(..., run_in_background=true)`, write the verdict to the journal asynchronously, and let the next session's Phase 1 read the verdict. This preserves crash recovery (Q-A6) without depending on a follow-up turn.

### D5 — `.panther-ivy/observability/` retention — **WARNING (W4)**

Add the same `find -mtime +7 -type d -exec rm -rf {} \;` pattern that `detect-ivy-workspace.sh:83` uses for the workspace-scoped observability directory, but scope it to `.panther-ivy/observability/sessions/` and run it from a SessionStart hook (alongside `cleanup-stale-pids.sh`). Bound the retention to 7 days unless the workspace has unsynced journal entries that reference older sessions.

### D6 — `clean=True` schema fix — **WARNING (J3)**

Two options: (a) remove the `clean` field from the `session_end` payload entirely (it adds no information); (b) add a SessionEnd-side sweeper that detects sessions with no `session_end` event in the journal (because the Stop hook never fired) and writes `clean=False` retroactively on the next SessionStart. Option (b) is more informative; option (a) is simpler. Use `AskUserQuestion` to decide before applying.

### D7 — `skills/build-ops/references/phase-5-quality-gate.md:58` — **INFO (C1, secondary site)**

Rewrite "Run full verification before wrapping up" to "Run full verification at the end of this build phase, before transitioning to the next phase." Removes the session-end framing.

---

## Appendix — voting-rule arithmetic table (Lens 5d full enumeration)

| Verdict 1 | Verdict 2 | Verdict 3 | Outcome | Halt? | Reconcile? |
|---|---|---|---|---|---|
| SOUND | SOUND | SOUND | proceed | no | no |
| SOUND | SOUND | ABSTAIN | proceed | no | no |
| SOUND | SOUND | UNSOUND | ABSTAIN | no | yes |
| SOUND | ABSTAIN | ABSTAIN | ABSTAIN; gather more evidence | no | re-dispatch |
| SOUND | UNSOUND | UNSOUND | halt; AskUserQuestion | yes | n/a |
| SOUND | UNSOUND | ABSTAIN | ABSTAIN | no | yes |
| ABSTAIN | ABSTAIN | ABSTAIN | re-dispatch with broader evidence | no | re-dispatch |
| ABSTAIN | ABSTAIN | UNSOUND | ABSTAIN | no | yes |
| ABSTAIN | UNSOUND | UNSOUND | halt; AskUserQuestion | yes | n/a |
| UNSOUND | UNSOUND | UNSOUND | halt; AskUserQuestion | yes | n/a |

Outcome column is sound — every row in which UNSOUND appears at least once forces ABSTAIN-reconcile or halt. The procedural ambiguity is in *what reconcile means* (Lens 5d), not in the arithmetic itself.

---

## Appendix — INSUFFICIENT_DATA marker for empirical verdict counts

`.panther-ivy/` directory does not exist anywhere in the plugin tree. No `.panther-ivy/journal-archive/*.yaml` files. No `gate_verdict` events in any non-test, non-`.harness-audit/` `*.yaml` or `*.jsonl` file. Empirical SOUND : UNSOUND : ABSTAIN distribution per gate cannot be computed from this worktree.

A follow-up audit after at least one representative protocol session (a few full build → verify → review cycles, ~20 gate dispatches) can re-grade this lens. The journal-archive rotation is automatic, so the data will accumulate naturally as the plugin is used.

---

## Considerations

**Pro.** The audit found four distinct named-reference drift surfaces the morning audit missed (Stop-hook skill ref, meta workflow agent ref, two auto-loaded rule files, test schema). Each is concretely identified at file:line with a unified-diff or description-only fix. The empirical self-eval check returned `INSUFFICIENT_DATA` honestly rather than fabricating a verdict.

**Con.** The empirical verdict-distribution check could not be exercised on this worktree because no workflow has yet run end-to-end here. The adversarial design probe failed to falsify only conditional on the agents calling their independent counter-source tools — so the design is robust by self-discipline, not by enforcement. D3 is the recommendation but not a deterministic patch. The voting-rule fix in Patch 5 hardens the reconciliation procedure but doesn't actually prevent a model under pressure from re-interpreting "re-dispatch" as "I re-read it in my own context, that counts."

**Alternatives considered.** (1) Replace text. Replacing the morning report rather than supplementing it — rejected by user. (2) Skip Phase 1. Skipping the three reviewer re-runs would have saved ~25k tokens, but would have missed the new INFO findings that surfaced today (e.g. the `tool-catalog.md:429` TODO and the seventh dead skill name at `skills/ivy-syntax/SKILL.md:47`). (3) Stop at structural self-eval. Skipping the empirical + adversarial probe in favour of a structural-only finding would have been faster but less defensible — and would have missed the discovery that the reviewer DOES have an independent counter-source via `ivy_rfc`, which falsifies the "shared-workspace bias" framing originally proposed.
