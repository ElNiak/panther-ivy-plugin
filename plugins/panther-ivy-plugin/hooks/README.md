# Hooks

<purpose>
Hook registrations for the panther-ivy-plugin live in `hooks.json`.
Individual script files live under `hooks/scripts/` (see
`hooks/scripts/README.md` for naming conventions). The full
tool-lifecycle reference, including matchers and observability schema,
lives in `skills/ivy-toolkit/references/hook-lifecycle.md`.
</purpose>

## PostToolUse Ordering for `Write|Edit`

Three separate `PostToolUse` entries match `Write|Edit`. Claude Code fires hooks in the order they appear in `hooks.json`. For `.ivy` file writes, the order is:

<instructions>
  <step n="1">`post-write-ivy-lint.sh` — runs `ivy_diagnostics(mode="structural")` on the edited file and prints a short pass/fail summary. Fast (~100 ms), non-blocking.</step>
  <step n="2">`post-write-workflow-aware.py` — reads the active workflow phase from `.panther-ivy/active-workflow` and advances or annotates the workflow state if the edit lands within a phase the workflow cares about.</step>
  <step n="3">`assess-modeling.py` and `assess-testspec.py` — adversarial G2 / G3 critics that analyse modeling and test-spec quality. They may write `[GAP: #NN …]` markers via the orchestrator path (see `.claude/rules/gap-markers.md`).</step>
</instructions>

<context>
Implicit dependency: `post-write-workflow-aware.py` reads workflow state
that `track-workflow-skill.py` writes on Skill invocations.
`assess-modeling.py` / `assess-testspec.py` consult the workflow state
too. If you add a new PostToolUse hook that depends on workflow state,
register it after `post-write-workflow-aware.py`; if it should run
before the adversarial assessors, register it between entries 2 and 3.
</context>

**State read by each script:**

| Script | Reads | Writes |
|---|---|---|
| `post-write-ivy-lint.sh` | edited file | stderr (diagnostics summary) |
| `post-write-workflow-aware.py` | `.panther-ivy/active-workflow`, edited file path | `.panther-ivy/workflow-journal` entries |
| `assess-modeling.py` | edited file + workflow state | `[GAP: #NN]` markers via orchestrator; JSONL events |
| `assess-testspec.py` | edited test spec + workflow state | `[GAP: #NN]` markers; JSONL events |

When debugging, inspect the JSONL observability log (`observe.py --event PostToolUse`) to see which hooks fired in which order for a given tool call.

## Related References

- `hooks/scripts/README.md` — script-naming convention (kebab vs. snake case).
- `skills/ivy-toolkit/references/hook-lifecycle.md` — full per-event reference (SessionStart, PreToolUse, PostToolUse, Stop, UserPromptSubmit, Notification).
- `.claude/rules/gap-markers.md` — the `[GAP: #NN]` marker contract that the G2/G3/G4/G5 adversarial hooks write.

<integration
  related-skills="ivy-toolkit (hook-lifecycle reference), reflection-patterns (G2/G3/G4/G5 dispatch)"
  related-rules=".claude/rules/gap-markers.md"
  state-files=".panther-ivy/active-workflow, .panther-ivy/workflow-journal"
  observability="JSONL events under $IVY_OBSERVABILITY_DIR/sessions/"/>
