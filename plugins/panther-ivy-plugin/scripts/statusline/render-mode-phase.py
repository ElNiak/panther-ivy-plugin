#!/usr/bin/env python3
"""Statusline segment: Mode/Phase indicator from PROJECT.md.

Outputs a single line like ``Mode: SCAFFOLD | Phase: 4/10 (core stack)``
when the active workspace has a PROJECT.md with mode != idle. Outputs
nothing otherwise (always-on default per audit Section 1; quiet when
idle).

Usage:
    python3 render-mode-phase.py            # cwd-relative resolution
    python3 render-mode-phase.py --root /path/to/worktree

Resolution rules:
  1. Active workspace name = ``.ivy-workspace-state.json`` key
     ``active_group`` under the resolved root.
  2. PROJECT.md path = ``<root>/protocol-testing/<active_group>/PROJECT.md``.
  3. If either is missing or PROJECT.md.mode == "idle", emit nothing.

Exit code is always 0; the statusline pipeline suppresses all output if
any segment exits non-zero.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# scripts/statusline/render-mode-phase.py -> plugin root is parents[2]
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

from hook_utils import read_active_workspace  # noqa: E402
from project_md_state import (  # noqa: E402
    ProjectMdSchemaError,
    load_project_md,
    resolve_project_md_path,
    resolve_protocol_dir,
)

_PHASE_NAMES = {
    1: "RFC ingest",
    2: "decompose",
    3: "types",
    4: "core stack",
    5: "entities",
    6: "behaviors",
    7: "test specs",
    8: "verify",
    9: "compile",
    10: "IUT",
}


def _resolve_root(arg_root: Path | None) -> Path:
    if arg_root is not None:
        return arg_root
    env_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Mode/Phase statusline segment.")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args()

    root = _resolve_root(args.root)
    state_path = root / ".ivy-workspace-state.json"
    workspace = read_active_workspace(str(state_path) if state_path.exists() else None)
    if not workspace:
        return 0
    project_md = resolve_project_md_path(resolve_protocol_dir(root, workspace))
    try:
        state = load_project_md(project_md)
    except (OSError, ProjectMdSchemaError):
        return 0
    if state["mode"] == "idle":
        return 0
    phase_name = _PHASE_NAMES.get(state["phase"], "")
    suffix = f" ({phase_name})" if phase_name else ""
    print(f"Mode: {state['mode'].upper()} | Phase: {state['phase']}/10{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
