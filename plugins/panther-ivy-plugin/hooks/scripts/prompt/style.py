#!/usr/bin/env python3
"""UserPromptSubmit hook: compose per-workflow style overlay + summary."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output, read_stdin  # noqa: E402
from lib.style_utils import compose_style, resolve_plugin_root  # noqa: E402
from lib.workflow_state import WorkflowContext  # noqa: E402


def main() -> int:
    read_stdin()  # consume stdin to avoid broken pipe

    plugin_root = resolve_plugin_root()
    ctx = WorkflowContext.current()
    workflow, phase = (ctx.workflow, ctx.phase) if ctx else (None, None)

    try:
        style_doc = compose_style(plugin_root, workflow, phase)
    except FileNotFoundError:
        return 0  # missing overlay file -> silent
    except Exception:
        return 0  # corrupt state -> silent

    if not style_doc:
        if workflow:
            print(
                f"WARN: compose-style.py: overlay for workflow '{workflow}' not found",
                file=sys.stderr,
            )
        return 0

    emit_hook_output(
        "UserPromptSubmit",
        system_message=f"[ivy-style] composed overlay for {workflow}/{phase}",
        additional_context=style_doc,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
