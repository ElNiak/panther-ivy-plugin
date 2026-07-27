#!/usr/bin/env python3
"""SessionStart hook: verify the journaling contract is present and parseable before the panther-ivy-plugin loads.

This is the fail-loud surface for the journaling contract. Phase 0 verification
(2026-04-30) showed SubagentStart exit-2 does NOT block dispatch, so the hook
that delivers the contract directive on subagent dispatch cannot be the
fail-loud surface. SessionStart hooks do block — see inject-using-plugin.sh
precedent — so we move the precondition check here.

Failure modes blocked:
  - Contract file missing.
  - Contract file unreadable (permission, IO error).
  - Contract file present but stripped of mandatory section headers (someone
    accidentally truncated or replaced the file).

On any failure: stderr message + exit 2. The plugin will not load.
On success: emits a brief [ivy-contract] systemMessage so the user sees the
precondition fired and passed.
"""

import os
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output


CONTRACT_REL_PATH = ".claude/rules/journaling-contract.md"

REQUIRED_HEADERS = (
    "# Journaling Contract",
    "## 1. Surface taxonomy",
    "## 2. Per-turn lifecycle",
    "## 3. Event payload schemas",
    "## 4. Idempotency, plan-mode, and concurrency",
    "## 5. Terminal-state HARD-GATE",
    "## 6. Subagent return shapes",
    "## 7. Hook output prefixes",
    "## 8. User-facing terminal-state message format",
    "## 9. Failure modes",
)


def main() -> int:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        sys.stderr.write(
            "panther-ivy-plugin: CLAUDE_PLUGIN_ROOT not set; cannot locate journaling contract\n"
        )
        return 2

    contract_path = os.path.join(plugin_root, CONTRACT_REL_PATH)
    if not os.path.isfile(contract_path):
        sys.stderr.write(
            f"panther-ivy-plugin: journaling contract missing at {contract_path};"
            + " the plugin cannot load without it\n"
        )
        return 2

    try:
        with open(contract_path, "r", encoding="utf-8") as fh:
            body = fh.read()
    except OSError as exc:
        sys.stderr.write(
            f"panther-ivy-plugin: journaling contract unreadable at {contract_path}: {exc}\n"
        )
        return 2

    missing = [h for h in REQUIRED_HEADERS if h not in body]
    if missing:
        sys.stderr.write(
            f"panther-ivy-plugin: journaling contract at {contract_path}"
            + f" is missing required section headers: {missing}\n"
        )
        return 2

    emit_hook_output(
        "SessionStart",
        system_message="[ivy-contract] journaling contract verified",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
