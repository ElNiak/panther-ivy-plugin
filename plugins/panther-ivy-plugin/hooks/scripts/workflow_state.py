#!/usr/bin/env python3
"""Read/write utilities for workflow state files.

State files live at ``<protocol_dir>/.panther-ivy/`` and track active
workflow context and multi-session build progress.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hook_utils import get_workspace_root

_STATE_DIR_NAME = ".panther-ivy"
_ACTIVE_WORKFLOW_FILE = "active-workflow"
_BUILD_STATE_FILE = "build-state.yaml"


def find_protocol_dir(protocol: str | None = None) -> str | None:
    """Find protocol directory from env var or by scanning cwd parents.

    Args:
        protocol: Optional protocol name (e.g. ``"bgp"``, ``"quic"``).
            When provided, the returned path is narrowed to
            ``protocol-testing/<protocol>/`` and validated to exist.

    Returns:
        Absolute path to the protocol directory, or None if not found.
    """
    root: str | None = None

    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        candidate = os.path.join(ws_root, "protocol-testing")
        if os.path.isdir(candidate):
            root = candidate

    if root is None:
        ws = get_workspace_root()
        candidate = os.path.join(ws, "protocol-testing")
        if os.path.isdir(candidate):
            root = candidate

    if root is None:
        return None

    if protocol is not None:
        specific = os.path.join(root, protocol)
        return specific if os.path.isdir(specific) else None

    return root


def _state_dir(protocol_dir: str) -> Path:
    """Returns the ``.panther-ivy`` state directory inside *protocol_dir*."""
    return Path(protocol_dir) / _STATE_DIR_NAME


def get_active_workflow(protocol_dir: str) -> dict | None:
    """Read the active-workflow YAML file.

    Returns:
        Parsed dict, or None if the file does not exist or is corrupt.
    """
    path = _state_dir(protocol_dir) / _ACTIVE_WORKFLOW_FILE
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
    except (OSError, yaml.YAMLError):
        return None


def set_active_workflow(
    protocol_dir: str,
    workflow: str,
    phase: str,
    invocation_depth: int = 0,
    caller: str | None = None,
) -> None:
    """Write the active-workflow YAML file.

    Args:
        protocol_dir: Path to the protocol directory.
        workflow: Name of the active workflow.
        phase: Current phase within the workflow.
        invocation_depth: Nesting depth for recursive invocations.
        caller: Optional identifier of the caller that set the workflow.
    """
    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "workflow": workflow,
        "phase": phase,
        "invocation_depth": invocation_depth,
        "started": datetime.now(timezone.utc).isoformat(),
    }
    if caller is not None:
        data["caller"] = caller

    with open(state_path / _ACTIVE_WORKFLOW_FILE, "w") as f:
        yaml.safe_dump(data, f)


def update_workflow_phase(protocol_dir: str, phase: str) -> None:
    """Update only the phase field in the existing active-workflow file."""
    data = get_active_workflow(protocol_dir)
    if data is None:
        return
    data["phase"] = phase
    with open(_state_dir(protocol_dir) / _ACTIVE_WORKFLOW_FILE, "w") as f:
        yaml.safe_dump(data, f)


def clear_active_workflow(protocol_dir: str) -> None:
    """Delete the active-workflow file."""
    path = _state_dir(protocol_dir) / _ACTIVE_WORKFLOW_FILE
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def is_workflow_stale(protocol_dir: str, max_age_hours: int = 2) -> bool:
    """Check if the active workflow's started timestamp exceeds *max_age_hours*.

    Returns:
        True if the workflow is stale or the timestamp cannot be parsed.
        False if within the allowed age or no active workflow exists.
    """
    data = get_active_workflow(protocol_dir)
    if data is None:
        return False
    started_raw = data.get("started")
    if not started_raw:
        return True
    try:
        started = datetime.fromisoformat(str(started_raw))
    except (ValueError, TypeError):
        return True
    age = datetime.now(timezone.utc) - started
    return age.total_seconds() > max_age_hours * 3600


def get_build_state(protocol_dir: str) -> dict | None:
    """Read build-state.yaml.

    Returns:
        Parsed dict, or None if the file does not exist.
    """
    path = _state_dir(protocol_dir) / _BUILD_STATE_FILE
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None


def set_build_state(protocol_dir: str, state_dict: dict) -> None:
    """Write build-state.yaml."""
    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)
    with open(state_path / _BUILD_STATE_FILE, "w") as f:
        yaml.safe_dump(state_dict, f)
