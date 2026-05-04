"""Scaffold-state YAML read/write helpers.

Manages ``<protocol_dir>/.panther-ivy/scaffold-state.yaml`` — the
persistent per-session scaffold progress file.
"""

import sys
from pathlib import Path

import yaml

from lib.workflow_state.context import (
    _SCAFFOLD_STATE_FILE,
    _state_dir,
)


class ScaffoldStateParseError(Exception):
    """Raised when ``scaffold-state.yaml`` exists but fails YAML parse.

    Distinguishes parse failure (file is present but corrupt — caller must
    handle / back up) from missing-file (benign — caller treats as a fresh
    build session).

    MCP-surfacing status (2026-04-23): SKILL.md workflow bodies call state
    ops via the ``ivy_workflow_state`` MCP tool, not via this Python module
    directly, so they cannot catch ``ScaffoldStateParseError`` as an exception.
    Consuming this exception from navigate / scaffold requires adding an MCP
    action in the ivy-lsp submodule (e.g. ``ivy_workflow_state(
    action="get_build")`` that distinguishes missing-file from parse-
    failure in its error surface). Until then this exception is consumed
    only by in-process Python callers: unit tests, hooks (via
    :func:`get_scaffold_state_safe`), and future CLI tooling.
    """


def get_scaffold_state(protocol_dir: str) -> dict | None:
    """Read ``<protocol_dir>/.panther-ivy/scaffold-state.yaml``.

    Returns:
        None if the file does not exist.
        dict if the file parses successfully.

    Raises:
        ScaffoldStateParseError: the file exists but YAML parse fails, or the
            parse yields a non-dict root. Includes the underlying parse
            error's message and the file path for caller diagnostics.
    """
    path = _state_dir(protocol_dir) / _SCAFFOLD_STATE_FILE
    if not path.exists():
        return None
    try:
        with open(path) as f:
            parsed = yaml.safe_load(f)
    except OSError as exc:
        raise ScaffoldStateParseError(
            f"could not read scaffold-state.yaml at {path}: {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ScaffoldStateParseError(
            f"YAML parse error in {path}: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ScaffoldStateParseError(
            f"expected a dict at {path} root, got {type(parsed).__name__}"
        )
    return parsed


def get_scaffold_state_safe(protocol_dir: str) -> dict | None:
    """Hook-friendly wrapper: returns None on BOTH missing file and parse failure.

    Passive observers (hook scripts, status-line renderers) that want to
    continue gracefully when ``scaffold-state.yaml`` is corrupt should call this
    wrapper instead of :func:`get_scaffold_state`. Workflow bodies that own the
    file (scaffold Phase 2 Step 2) should call :func:`get_scaffold_state` directly
    and handle :class:`ScaffoldStateParseError` with user-visible recovery.

    The parse failure is swallowed but reported once per process to
    ``sys.stderr`` so the user can investigate, without the hook itself
    raising.
    """
    try:
        return get_scaffold_state(protocol_dir)
    except ScaffoldStateParseError as exc:
        if "workflow_state" not in sys.modules or not getattr(
            sys.modules[__name__], "_SCAFFOLD_STATE_WARNED", False
        ):
            msg = f"WARN: get_scaffold_state_safe swallowed parse failure at {protocol_dir}: {exc}"
            print(msg, file=sys.stderr)
            setattr(sys.modules[__name__], "_SCAFFOLD_STATE_WARNED", True)
        return None


def set_scaffold_state(protocol_dir: str, state_dict: dict) -> None:
    """Write scaffold-state.yaml."""
    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)
    with open(state_path / _SCAFFOLD_STATE_FILE, "w") as f:
        yaml.safe_dump(state_dict, f)
