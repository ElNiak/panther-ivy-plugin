# Changelog

All notable changes to the `panther-ivy-plugin` Claude Code plugin are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

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
