#!/usr/bin/env python3
"""UserPromptSubmit hook: inject workflow-aware output style as additionalContext.

Reads the active workflow state, composes base style + workflow overlay
(with active phase highlighted), and outputs as additionalContext JSON.

Non-blocking -- always exits 0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from style_utils import compose_style, resolve_plugin_root
from workflow_state import find_protocol_dir, get_active_workflow


def main():
    read_stdin()  # consume stdin to avoid broken pipe

    plugin_root = resolve_plugin_root()
    protocol_dir = find_protocol_dir()

    workflow = None
    phase = None
    if protocol_dir:
        state = get_active_workflow(protocol_dir)
        if state:
            workflow = state.get("workflow")
            phase = state.get("phase")

    style_doc = compose_style(plugin_root, workflow, phase)
    if not style_doc:
        sys.exit(0)

    emit_hook_output("UserPromptSubmit", additional_context=style_doc)


if __name__ == "__main__":
    main()
