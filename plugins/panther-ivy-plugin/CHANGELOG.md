# Changelog

All notable changes to the `panther-ivy-plugin` Claude Code plugin are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- **Workflow state model refactored (cluster 1 of the 2026-04-23 workflow audit follow-ups).** The `active-workflow` YAML schema drops `invocation_depth` and `caller`, reducing to three fields: `workflow`, `phase`, `started`. Workflow composition now rides on a new `pending_dispatch` journal event: a workflow that needs another workflow to run next appends `pending_dispatch(target_workflow=<next>, reason=<why>)` and clears its own flag; navigate's Phase 1 Step 2c consumes the event (same-turn when the harness routes in-line, next-turn otherwise), writes a paired `workflow_resumed` idempotency marker, and dispatches the target. `track-workflow-skill.py` simplifies to a single-branch overwrite pattern (same-workflow re-entry remains a no-op to preserve `started`). `WorkflowContext` drops the same fields; legacy `invocation_depth`/`caller` keys in older YAML are surfaced once as unknown-field WARNs and then ignored.
- Every workflow's "On Completion" prose is a single action: append an optional `pending_dispatch`, then clear the active-workflow flag. No more decrement/restore branches. Rule #37 ("every workflow returns to navigate on completion") is canonical and unqualified.
- `reflection-patterns` Pattern A (Reflection Gate) fires unconditionally. The "Skip check if `invocation_depth > 0`" step is removed — every workflow is a top-level frame from the state machine's perspective, so there is no sub-workflow to skip for.
- Triage gains a mode-based invocation split: `args="preflight"` runs Phase 1 read-only as a caller-inline health check (no state writes, no dispatch); `args="full-health-check"` runs the 9-step deep runbook; direct invocation runs the full Phase 1–3 cycle interactively. Navigate, verify, build, and review's preflight steps call `Skill(skill="panther-ivy-plugin:workflow-triage", args="preflight")` with no caller/depth bookkeeping.

### Fixed
- **Cluster 3 (bundled):** `build` workflow gains a Phase 0 plan-mode preamble matching verify's and review's treatment. Build no longer attempts to scaffold or compile `.ivy` files when plan mode is active; instead it routes to Plan-Author drafting with a `plan_approved` handoff.
- **Cluster 4 (bundled):** verify Phase 5 IUT testing now runs unconditionally on Phase 4 PASS. The pre-existing `invocation_depth > 0` skip guard — which had caused IUT testing to be silently bypassed in `build → verify` chains — is deleted. Any verify run reaching Phase 4 PASS proceeds through Phase 5.
- **Cluster 2/5 (bundled):** every workflow's "On Completion" prose is now one line; navigate's orphaned "Task 3" and "defined later in this skill" anchor references are replaced with explicit section-heading links; the `"navigate/init"` shorthand string in the Phase 1 Step 1 note is rewritten to the explicit `workflow="workflow-navigate", phase="init"` pair.

### Migration notes
- `set_active_workflow()` no longer accepts `invocation_depth` or `caller` keyword arguments. Callers that passed them hit `TypeError`; they should drop the arguments.
- A stored `active-workflow` YAML file from a prior session that still contains `invocation_depth` and `caller` is tolerated: the unknown keys are dropped with a one-shot WARN on `sys.stderr`. No migration script is required.
- `pending_dispatch` TTL: pending-dispatch entries older than the 2-hour staleness threshold (the same threshold as `active-workflow`) are ignored by navigate's Phase 1 Step 2c. A stalled chain left over from a prior session is not resumed silently.

## [0.11.0] — 2026-04-28 — Orchestrator refactor (approach E)

### Added
- `skills/ivy/` orchestrator skill (single entry point).
- 5 workflow ops-skills (`triage-ops`, `build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops`).
- 5 workflow specialist agents (`ivy-{triage,builder,verifier,reviewer,meta}-agent`).
- 3 gate-critic agents (`g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`).
- `scripts/migrate-active-workflow.sh` one-shot YAML schema migration.
- `systemMessage` output key on every kept hook with non-trivial output (Phase D table).

### Changed
- 7 `knowledge-*` skills renamed to bare names (`ivy-toolkit`, `ivy-syntax`, etc.) and restructured to thin SKILL.md (≤80 LOC) + on-demand references/.
- Hook footprint slimmed from 34 to 28 scripts.
- Rewrote directives in 4 gate-firing scripts (dropped reflection-patterns reference, renamed workflow filter).
- `check-workspace-scope.py` deny message uses `ivy_workspace` MCP tool.
- `inject-using-plugin.sh` primer points at `panther-ivy-plugin:ivy` orchestrator.
- 5 of 13 `.claude/rules/` rewritten (iron-laws, gap-markers, output-style, postuse-hook-ordering, skill-conventions).

### Removed
- `routing-rules.json` (programmatic dispatch deprecated; orchestrator description owns activation).
- 6 hook scripts (`compose-style`, `route-user-prompt`, `track-workflow-skill`, `auto-load-skill-references`, `interaction-checkpoint`, `tip-shown`) → `.backup/2026-04-28/`.
- 5 commands (`nct-check`, `nct-compile`, `nct-learn`, `nct-model-info`, `nct-observability`).
- 3 output styles (`ivy-default`, `ivy-audit`, output-styles/README.md).
- 11 deprecated skills (`workflow-*`, `cross-cutting-*`, `meta-using-panther-ivy-plugin`, `meta-plugin-self-mod`) → `.backup/2026-04-28/skills/`.
- 4 deprecated specialist agents (`spec-analyst`, `model-reviewer`, `traceability-agent`, `plugin-conventions-reviewer`) → `.backup/2026-04-28/agents/`.

### Migration notes
- Run `scripts/migrate-active-workflow.sh <protocol-testing-root>` once to rewrite `.panther-ivy/active-workflow` files from `workflow: workflow-verify` schema to `workflow: verify`.
- Workspace scope via `ivy_workspace(action='set'|'clear', target='<name>')` MCP tool, not slash commands. Workflow tracking via `ivy_workflow_state(action='set', workflow='<name>', phase='<phase>', protocol='<name>')` MCP tool (separate from `ivy_workspace`).
- Stale `panther-ivy-plugin 2/` duplicate tree left untouched per the standing memory rule on backup retention.

## [0.10.0] — 2026-04-21

### Removed
- `ivy-lsp` plugin entry. The Ivy LSP is already declared in this plugin's own `.lsp.json`; the duplicate entry was incomplete (no `plugin.json`, missing launcher `lsp-start.sh`) and has been dropped from `marketplace.json`.
- `session-retrospective` skill. Its behavior is merged into `knowledge-capture`, which is now user-invocable.

### Changed
- `knowledge-capture` is now user-invocable and covers both session learning capture and skill/reference auditing. All existing workflow phases and `/nct-learn` continue to load this skill unchanged.
- Workflow-state lookups in hook scripts now use the new `WorkflowContext.current()` classmethod on `hooks/scripts/workflow_state.py`. The underlying primitives (`find_protocol_dir`, `get_active_workflow`) are unchanged. Note: `current()` returns `None` when the active-workflow YAML is missing the required `workflow` or `phase` keys, even if `find_protocol_dir` resolves — this protects callers from partial/corrupt state files. Unknown YAML keys are silently dropped so schema additions don't crash the dataclass.
- Plugin version is now declared only in `.claude-plugin/plugin.json`. The marketplace entry no longer sets a `version` field, per the Claude Code plugin docs' recommendation to avoid silent drift.

### Not addressed
- Known reliability issues flagged in `REVIEW.md` (shell quoting in `scripts/workspace-common.sh`, `cleanup-ivy-lsp.sh` session-isolation bug, 8 failing tests, wider skill audit) remain open. They will be handled in a follow-up reliability-hardening release.
