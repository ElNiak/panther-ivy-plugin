# Hooks

<purpose>
Hook registrations for the panther-ivy-plugin live in `hooks.json`.
Individual script files live under `hooks/scripts/` (see
`hooks/scripts/README.md` for naming conventions). The full
tool-lifecycle reference, including matchers and observability schema,
lives in `skills/ivy-toolkit/references/hook-lifecycle.md`.
</purpose>

## Related References

- `hooks/scripts/README.md` — script-naming convention (kebab vs. snake case).
- `skills/ivy-toolkit/references/hook-lifecycle.md` — full per-event reference (SessionStart, PreToolUse, PostToolUse, Stop, UserPromptSubmit, Notification).
- `.claude/rules/gap-markers.md` — the `[GAP: #NN]` marker contract that the G2/G3/G4/G5 adversarial hooks write.

<integration
  related-skills="ivy-toolkit (hook-lifecycle reference), reflection-patterns (G2/G3/G4/G5 dispatch)"
  related-rules=".claude/rules/gap-markers.md"
  state-files=".panther-ivy/active-workflow, .panther-ivy/workflow-journal"
  observability="JSONL events under $IVY_OBSERVABILITY_DIR/sessions/"/>
