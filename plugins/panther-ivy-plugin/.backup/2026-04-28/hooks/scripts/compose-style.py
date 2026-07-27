#!/usr/bin/env python3
"""UserPromptSubmit hook: inject workflow overlay as additionalContext.

Reads the active workflow state and injects the workflow overlay
(with active phase highlighted) as additionalContext JSON. Base
formatting conventions are handled by output styles at session level.

Non-blocking -- always exits 0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from style_utils import compose_style, resolve_plugin_root
from workflow_state import WorkflowContext


def main():
    read_stdin()  # consume stdin to avoid broken pipe

    plugin_root = resolve_plugin_root()
    ctx = WorkflowContext.current()
    workflow, phase = (ctx.workflow, ctx.phase) if ctx else (None, None)

    style_doc = compose_style(plugin_root, workflow, phase)
    if not style_doc:
        if workflow:
            print(
                f"WARN: compose-style.py: overlay for workflow '{workflow}' not found",
                file=sys.stderr,
            )
        sys.exit(0)

    emit_hook_output("UserPromptSubmit", additional_context=style_doc)


if __name__ == "__main__":
    main()
