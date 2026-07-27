#!/usr/bin/env python3
"""SessionStart hook: inject the panther-ivy-plugin orchestrator priming.

After the orchestrator refactor, the orchestrator skill is
``panther-ivy-plugin:ivy``. Workspace control happens via the ``ivy_workspace``
MCP tool, not slash commands. This hook surfaces that contract once at
session start so the model has the routing rules in context.

The bash predecessor (``inject-using-plugin.sh``) put ``systemMessage``
inside ``hookSpecificOutput`` — same envelope-shape bug as the original
``inject-journaling-contract.py`` private ``emit()``. The Python rewrite
fixes that by going through ``emit_hook_output``.
"""

from __future__ import annotations

import os
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output  # noqa: E402


_PRIMER = (
    "[panther-ivy-plugin priority overview]\n\n"
    "# Using panther-ivy-plugin\n\n"
    "## 1% rule\n"
    "If a panther-ivy-plugin skill might apply (even at 1% probability), "
    "invoke it via the `Skill` tool. When ambiguous, default to "
    '`Skill(skill="panther-ivy-plugin:ivy")` — the orchestrator routes to '
    "the right specialist or answers from its own references.\n\n"
    "User instructions override skills; iron laws "
    "(`.claude/rules/iron-laws.md`) override both.\n\n"
    "## Methodology routing (handled by orchestrator)\n"
    "- **NCT** (compliance) — build → verify → review.\n"
    "- **NACT** (security) — build → verify, attack-pattern scope.\n"
    "- **NSCT** (simulation) — build emits experiment-config sidecar.\n\n"
    "## Iron laws (enforced by orchestrator + auto-loaded rule)\n"
    "- `NO_FIX_WITHOUT_VERIFY` (verify): no resolution claim without "
    "fresh `ivy_verify`/`ivy_compile` this turn.\n"
    "- `NO_LAYER_WITHOUT_SCAFFOLD` (build): "
    "`ivy_diagnostics(mode=structural)` SOUND on predecessor before new layer.\n"
    "- `NO_QUALITY_WITHOUT_COVERAGE` (review): every quality verdict cites "
    "`ivy_coverage`/`ivy_quality`.\n"
    "- `STALENESS_RULE` (all): re-run if include closure edited since "
    "prior result.\n\n"
    "## Workspace\n"
    'Active workspace via `ivy_workspace(action="get")`. To set: '
    '`ivy_workspace(action="set", target="<name>")`. To clear: '
    '`ivy_workspace(action="clear")`. Available targets: quic, apt, '
    "apt_quic, minip, bgp, coap, scaffolds (or a `.ivy` file path). "
    "Kwarg is `target=`, not `protocol=`.\n\n"
    "## Workflow tracking\n"
    "The orchestrator records active workflow + phase via "
    '`ivy_workflow_state(action="set", workflow="<name>", phase="<phase>", '
    'protocol="<name>")` (a separate MCP tool from `ivy_workspace`).\n\n'
    "For full detail invoke "
    '`Skill(skill="panther-ivy-plugin:ivy")` — the orchestrator\'s body has '
    "the dispatch tables, methodology decision logic, and gate-critic "
    "invocation patterns."
)


def main() -> None:
    emit_hook_output(
        "SessionStart",
        system_message="[panther-ivy] orchestrator preamble injected",
        additional_context=_PRIMER,
    )


if __name__ == "__main__":
    main()
