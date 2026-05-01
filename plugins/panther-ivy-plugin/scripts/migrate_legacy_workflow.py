#!/usr/bin/env python3
"""One-shot migration: rewrite legacy active-workflow YAMLs to canonical names.

Use cases:
  - Pre-Phase-C YAMLs (`workflow: workflow-verify`, etc.) are renamed to
    the post-Phase-2 canonical form. After the verify-ops split, legacy
    `workflow-verify` maps to the new `refine` workflow (refine owns the
    verify-cycle: compile -> ivy_verify -> diagnose -> fix). IUT execution
    moved to `experiment`; if a legacy `workflow-verify` YAML was at IUT
    phase, the user should manually re-set it to `experiment` post-migration.
  - The legacy `meta-plugin-self-mod` workflow is renamed to `meta`.
  - The obsolete `workflow-navigate` workflow has no canonical replacement
    (the orchestrator absorbed navigate's role); the file is DELETED rather
    than rewritten to avoid an active-workflow that points at a non-
    existent target.

Per `feedback_no_backward_compat_shims`, this script is one-shot: the user
invokes it explicitly to clean up legacy YAMLs after upgrading the plugin.
It is NOT called from any hook; in particular, `cleanup-stale-workflow.py`
does not perform normalize-on-read. This script is removable in a follow-up
commit once all known legacy YAMLs are migrated.

Usage:
    python <plugin>/scripts/migrate_legacy_workflow.py [--dry-run] [<root>]

Args:
    --dry-run: Print what would change but do not modify any file.
    <root>: Path containing protocol directories (default: ./protocol-testing).
        The script scans `<root>/*/.panther-ivy/active-workflow` files.

Supersedes: scripts/migrate-active-workflow.sh (had a navigate→ivy mapping
bug; missing meta-plugin-self-mod handling; no journal write).
"""

import argparse
import os
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", _SCRIPT_DIR.parent))
sys.path.insert(0, str(_PLUGIN_ROOT / "hooks" / "scripts"))

import yaml  # noqa: E402
from workflow_state import append_journal_event  # type: ignore[import-not-found]  # noqa: E402

_MIGRATION_MAP: dict[str, str | None] = {
    "workflow-build": "scaffold",
    "workflow-verify": "refine",
    "workflow-review": "review",
    "workflow-triage": "triage",
    "meta-plugin-self-mod": "meta",
    # Post-Phase-1, pre-Phase-2 unprefixed names get a second migration step.
    # `build` and `verify` were canonical between the prefix-removal commit and
    # the verify-ops split; both retire after Phase 2. `build` -> `scaffold`,
    # `verify` -> `refine` (refine owns the dominant prior verify-cycle usage;
    # if the existing YAML was at the IUT phase, manually re-set to `experiment`
    # post-migration).
    "build": "scaffold",
    "verify": "refine",
    "workflow-navigate": None,
}


def _migrate_one(active_path: Path, *, dry_run: bool) -> tuple[str, str | None]:
    """Migrate or skip a single active-workflow file.

    Returns:
        (action, message) where action is one of "migrated", "cleared",
        "skipped" and message is human-readable detail.
    """
    try:
        with active_path.open() as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        return "skipped", f"cannot parse {active_path}: {exc}"

    if not isinstance(data, dict) or "workflow" not in data:
        return "skipped", f"{active_path}: no 'workflow' field"

    current = data["workflow"]
    if current not in _MIGRATION_MAP:
        return "skipped", f"{active_path}: '{current}' already canonical or unknown"

    target = _MIGRATION_MAP[current]
    protocol_dir = str(active_path.parent.parent)

    if target is None:
        msg = f"{active_path}: '{current}' -> CLEAR (no canonical replacement)"
        if not dry_run:
            active_path.unlink()
            append_journal_event(
                protocol_dir,
                "decision",
                {
                    "summary": "Migrated legacy active-workflow (cleared)",
                    "context": f"'{current}' has no canonical replacement; file deleted",
                },
                workflow=None,
                phase=None,
            )
        return "cleared", msg

    msg = f"{active_path}: '{current}' -> '{target}'"
    if not dry_run:
        data["workflow"] = target
        with active_path.open("w") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False)
        append_journal_event(
            protocol_dir,
            "decision",
            {
                "summary": "Migrated legacy active-workflow name",
                "context": f"renamed '{current}' -> '{target}' per Phase-C/E rename",
            },
            workflow=target,
            phase=data.get("phase"),
        )
    return "migrated", msg


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0] if __doc__ else None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print actions without modifying files",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="protocol-testing",
        help="path containing protocol directories (default: ./protocol-testing)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    counts = {"migrated": 0, "cleared": 0, "skipped": 0}
    for active_path in sorted(root.glob("*/.panther-ivy/active-workflow")):
        action, message = _migrate_one(active_path, dry_run=args.dry_run)
        counts[action] += 1
        prefix = "[dry-run] " if args.dry_run and action != "skipped" else ""
        print(f"{prefix}{action}: {message}")

    suffix = " (dry-run; no files changed)" if args.dry_run else ""
    summary = (
        f"\nDone: {counts['migrated']} migrated,"
        + f" {counts['cleared']} cleared,"
        + f" {counts['skipped']} skipped{suffix}"
    )
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
