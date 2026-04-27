---
paths:
  - "hooks/hooks.json"
  - "hooks/scripts/post-*.py"
  - "hooks/scripts/post-*.sh"
---

# PostToolUse Hook Ordering

When editing PostToolUse hook configuration or scripts, preserve this ordering contract.

Three separate `PostToolUse` entries match `Write|Edit`. Claude Code fires hooks in the order they appear in `hooks.json`. For `.ivy` file writes, the required order is:

1. `post-write-ivy-lint.sh` — runs `ivy_diagnostics(mode="structural")` on the edited file and prints a short pass/fail summary. Fast (~100 ms), non-blocking.
2. `post-write-workflow-aware.py` — reads the active workflow phase from `.panther-ivy/active-workflow` and advances or annotates the workflow state if the edit lands within a phase the workflow cares about.
3. `assess-modeling.py` and `assess-testspec.py` — adversarial G2 / G3 critics that analyse modeling and test-spec quality. They may write `[GAP: #NN …]` markers via the orchestrator path (see `.claude/rules/gap-markers.md`).

**Why this order matters:** `post-write-workflow-aware.py` reads workflow state that `track-workflow-skill.py` writes on Skill invocations. `assess-modeling.py` and `assess-testspec.py` also consult the workflow state. If these assessors run before `post-write-workflow-aware.py`, they see stale workflow state and may annotate the wrong phase or skip phase-sensitive checks entirely. The lint hook runs first because it is fast and stateless — failing it early avoids invoking heavier hooks on a structurally broken file.

**State read by each script:**

| Script | Reads | Writes |
|---|---|---|
| `post-write-ivy-lint.sh` | edited file | stderr (diagnostics summary) |
| `post-write-workflow-aware.py` | `.panther-ivy/active-workflow`, edited file path | `.panther-ivy/workflow-journal` entries |
| `assess-modeling.py` | edited file + workflow state | `[GAP: #NN]` markers via orchestrator; JSONL events |
| `assess-testspec.py` | edited test spec + workflow state | `[GAP: #NN]` markers; JSONL events |

**Adding new hooks:** If you add a new PostToolUse hook that depends on workflow state, register it after `post-write-workflow-aware.py`. If it should run before the adversarial assessors, register it between entries 2 and 3.

When debugging hook execution order, inspect the JSONL observability log (`observe.py --event PostToolUse`) to see which hooks fired in which order for a given tool call.
