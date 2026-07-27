# Hook Scripts

## Language Convention

Every hook is Python 3. `hooks.json` invokes each script as
`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<path>.py`, so the scripts are
kept non-executable (`chmod 644`); any shebang line is documentary only.
This makes `hooks.json` the single source of truth for invocation — one
interpreter, one entry-point convention, no stale `+x` bits on edited
files.

The previous Bash hooks have been rewritten in Python and moved to
`.backup/hooks-shell-rewrite-2026-05-01/scripts/` for reference until the
next graduation sweep.

## Naming Convention

- **Hook entry points** (called by `hooks.json`): kebab-case
  (e.g., `mcp/health.py`).
- **Importable Python libraries** (shared utilities under `lib/`):
  snake_case per PEP 8 (e.g., `lib/hook_utils/`).
- **Observability subsystem** (`observability/`): snake_case for all
  files.

## Hook output discipline

Every hook emits its envelope through
`lib.hook_utils.emit_hook_output(event_name, system_message=..., …)`. The
helper raises `TypeError` if `system_message` is omitted; pass an empty
string to suppress the UI line. The `emit_noop(event_name, reason)`
helper is the canonical way to surface "this hook ran but took no
action" — the resulting `[ivy-noop] <reason>` system message lets the
user filter no-op lines from action-bearing ones.

```python
from lib.hook_utils import emit_hook_output, emit_noop

def main():
    if not _condition():
        emit_noop("PostToolUse", "non-.ivy file")
        return

    emit_hook_output(
        "PostToolUse",
        system_message="[ivy-foo] action taken",
        additional_context="Detail surfaced to the model.",
    )
```

A pytest at `tests/test_observability_write_discipline.py` AST-scans every
script and fails if any `emit_hook_output` call site omits `system_message`,
or if any script constructs a `hookSpecificOutput` envelope by hand instead
of going through the helper.

## Family Index

Each family folder has its own `README.md` with the per-hook table. The
parent file used to duplicate that detail; after the 2026-05-04 audit
follow-up the duplication is removed and this table is the canonical map.

| Folder | Purpose |
|---|---|
| [`cleanup/`](cleanup/README.md) | SessionStart / SessionEnd cleanup of stale PIDs, stale workflow flags, and the ivy-lsp sidecar. |
| [`journaling/`](journaling/README.md) | SessionStart contract check + SubagentStart contract injection. |
| [`lib/`](lib/README.md) | Shared Python utilities — **not user-facing hooks**. Imported by every other family. |
| [`mcp/`](mcp/README.md) | PreToolUse health/indexing gates, PostToolUseFailure auto-retry, Notification disconnect handling, MCP-tool activity flag. |
| [`observability/`](observability/README.md) | JSONL observability subsystem fired on every event. |
| [`posttooluse/`](posttooluse/README.md) | PostToolUse linters (`lint/`) and adversarial gate dispatchers (`gates/`). |
| [`pretooluse/`](pretooluse/README.md) | Residual PreToolUse hooks not in another family (currently the direct-CLI advisor). |
| [`prompt/`](prompt/README.md) | UserPromptSubmit hooks (style composition, plugin overview injection). |
| [`record/`](record/README.md) | Hooks that record events to the workflow journal and JSONL side-channels. |
| [`render/`](render/README.md) | Hooks that render tool results, project state, and session summaries. |
| [`session/`](session/README.md) | SessionStart hooks not in another family (`start/check-hook-paths.py`). |
| [`statusline/`](statusline/README.md) | Statusline cache sync + per-session overlay writes. |
| [`workspace/`](workspace/README.md) | SessionStart workspace detection + write-scope guarding + workspace-change notification. |

`hooks.json` remains the canonical source for event firing order; refer
to it (and the in-file ordering comments) when ordering matters. The
Stop sequence in particular runs `record/session-end.py` before
`render/summary/main.py` before `observability/observe.py`.

## See also

- `.claude/rules/journaling-contract.md` — journal event schemas and the session-activity flag.
- `.claude/rules/postuse-hook-ordering.md` — why PostToolUse hooks run in their current order.
- `.claude/rules/output-style.md` — `systemMessage` prefix table and T1/T2/T3 discipline.
