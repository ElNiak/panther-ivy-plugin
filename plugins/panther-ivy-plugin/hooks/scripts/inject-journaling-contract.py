#!/usr/bin/env python3
"""SubagentStart hook: emit a short directive pointing plugin specialists at
the journaling contract.

Per Phase 0 verification (2026-04-30, see feedback_subagent_start_semantics):
SubagentStart additionalContext is truncated at ~2KB and exit-2 does NOT
block dispatch. Therefore this hook emits a directive well under the cap and
relies on the agent body's mandatory first-action Read for full contract
delivery. Fail-loud on missing contract lives in the SessionStart precondition
hook (check-journaling-contract.py), not here.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.hook_utils import emit_hook_output
from lib.workflow_state import journal_path_template


SPECIALISTS = frozenset({
    "panther-ivy-plugin:ivy-builder-agent",
    "panther-ivy-plugin:ivy-refiner-agent",
    "panther-ivy-plugin:ivy-experimenter-agent",
    "panther-ivy-plugin:ivy-reviewer-agent",
    "panther-ivy-plugin:ivy-triage-agent",
    "panther-ivy-plugin:ivy-meta-agent",
})

CRITICS = frozenset({
    "panther-ivy-plugin:g-plan-critic",
    "panther-ivy-plugin:g-fidelity-critic",
    "panther-ivy-plugin:g-knowledge-critic",
})

CONTRACT_REL_PATH = ".claude/rules/journaling-contract.md"


def specialist_directive() -> str:
    return (
        "[ivy-journal] You are a panther-ivy-plugin specialist. Before any "
        "other tool call, Read the journaling contract at "
        f"${{CLAUDE_PLUGIN_ROOT}}/{CONTRACT_REL_PATH}. The contract has nine "
        "sections defining your journal-write discipline:\n"
        "  §1 Surface taxonomy — which surfaces write the journal\n"
        "  §2 Per-turn lifecycle decision tree\n"
        "  §3 Event payload schemas (closed list)\n"
        "  §4 Idempotency, plan-mode, concurrency\n"
        "  §5 Terminal-state HARD-GATE — your end-of-turn discipline\n"
        "  §6 Subagent return shapes (your output format)\n"
        "  §7 Hook output prefixes\n"
        "  §8 User-facing terminal-state message format\n"
        "  §9 Failure modes\n"
        "Skipping the Read is a workflow violation. Your ops-skill preloads "
        "the same contract; this directive guarantees you have it in context "
        "even if the ops-skill load is deferred."
    )


def critic_stub() -> str:
    return (
        "[ivy-journal] You are a panther-ivy-plugin critic. Return verdicts "
        f"only. Do not write to {journal_path_template()}. The "
        "orchestrator writes gate_verdict after aggregating your fan-out per "
        "the journaling contract §6.2."
    )


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (OSError, ValueError):
        return 0

    subagent_type = str(hook_input.get("subagent_type", "")).strip()
    if not subagent_type:
        return 0

    if subagent_type in SPECIALISTS:
        emit_hook_output(
            "SubagentStart",
            additional_context=specialist_directive(),
            system_message=f"[ivy-journal] contract directive injected for {subagent_type}",
        )
    elif subagent_type in CRITICS:
        emit_hook_output(
            "SubagentStart",
            additional_context=critic_stub(),
            system_message=f"[ivy-journal] critic stub injected for {subagent_type}",
        )
    elif subagent_type.startswith("panther-ivy-plugin:"):
        sys.stderr.write(
            f"inject-journaling-contract: unknown panther-ivy-plugin agent '{subagent_type}';"
            + " emitting critic stub as fail-safe default\n"
        )
        emit_hook_output(
            "SubagentStart",
            additional_context=critic_stub(),
            system_message=f"[ivy-journal] fail-safe stub for unknown agent {subagent_type}",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
