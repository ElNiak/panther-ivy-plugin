#!/usr/bin/env python3
"""One-shot bootstrap of PROJECT.md for every protocol-testing/<protocol>/.

Discovers protocol directories by scanning ``<root>/protocol-testing/`` for
subdirectories. Skips dirs that already have a PROJECT.md. Writes
mode=idle, phase=0 defaults so subsequent renders by the workflow-state
hook always have a file to overwrite.

Per ``feedback_no_backward_compat_shims``: this script is intentionally
one-shot and deletable after the first sweep across all known protocols.
Re-running is a no-op for already-bootstrapped directories.

Usage:
  python3 migrate-bootstrap-project-md.py             # cwd is the worktree root
  python3 migrate-bootstrap-project-md.py --root .   # explicit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

from lib.project_md_state import write_project_md  # noqa: E402


def _discover_protocol_dirs(root: Path) -> list[Path]:
    """Return every immediate subdirectory of ``<root>/protocol-testing/``."""
    parent = root / "protocol-testing"
    if not parent.is_dir():
        return []
    return sorted(p for p in parent.iterdir() if p.is_dir())


def _idle_state(protocol: str) -> dict:
    return {
        "protocol": protocol,
        "version": "unknown",
        "mode": "idle",
        "phase": 0,
        "journal_pointer": ".panther-ivy/workflow-journal.yaml#null",
        "last_verify": {"status": "NOT_RUN", "timestamp": None, "isolate": None},
        "rfc_sections_covered": [],
        "open_counterexamples": [],
        "last_iut_run": None,
        "deferred_layers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap PROJECT.md for every known protocol-testing/<protocol>/."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    bootstrapped = 0
    skipped = 0
    for target_dir in _discover_protocol_dirs(args.root):
        target = target_dir / "PROJECT.md"
        if target.exists():
            print(f"skip {target} (already exists)")
            skipped += 1
            continue
        write_project_md(target, _idle_state(target_dir.name))
        print(f"wrote {target}")
        bootstrapped += 1

    print(f"summary: {bootstrapped} bootstrapped, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
