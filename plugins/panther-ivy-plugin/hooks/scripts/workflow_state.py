#!/usr/bin/env python3
"""Read/write utilities for workflow state files.

State files live at ``<protocol_dir>/.panther-ivy/`` and track active
workflow context and multi-session build progress.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hook_utils import get_workspace_root

_STATE_DIR_NAME = ".panther-ivy"
_ACTIVE_WORKFLOW_FILE = "active-workflow"
_BUILD_STATE_FILE = "build-state.yaml"
_JOURNAL_FILE = "workflow-journal.yaml"
_JOURNAL_ARCHIVE_DIR = "journal-archive"

_VALID_EVENT_TYPES = frozenset({
    "session_start",
    "session_end",
    "decision",
    "phase_transition",
    "progress",
    "error",
    "context_switch",
    "gate_dispatched",
    "gate_verdict",
    "plan_approved",
    "workflow_resumed",
    "knowledge_captured",
})


def resolve_protocol_from_workspace(ws_root: str) -> str | None:
    """Read active workspace state to get current protocol.

    Checks ``.ivy-workspace-state.json`` for ``active_group`` first,
    then falls back to ``active_layers[0]``.
    """
    state_file = os.path.join(ws_root, ".ivy-workspace-state.json")
    if not os.path.exists(state_file):
        return None
    try:
        with open(state_file) as f:
            data = json.load(f)
        group = data.get("active_group")
        if group:
            return group
        layers = data.get("active_layers")
        if layers and isinstance(layers, list) and layers[0]:
            return layers[0]
        return None
    except (OSError, ValueError, TypeError):
        return None


def _find_protocol_testing_root() -> tuple[str | None, str | None]:
    """Locate the ``protocol-testing/`` directory and workspace root.

    Returns:
        (protocol_testing_root, workspace_root) or (None, None).
    """
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        candidate = os.path.join(ws_root, "protocol-testing")
        if os.path.isdir(candidate):
            return candidate, ws_root

    ws = get_workspace_root()
    candidate = os.path.join(ws, "protocol-testing")
    if os.path.isdir(candidate):
        return candidate, ws

    check = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(check, "protocol-testing")
        if os.path.isdir(candidate):
            return candidate, check
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent

    return None, None


def find_protocol_dir(protocol: str | None = None) -> str | None:
    """Find protocol directory from env var or by scanning cwd parents.

    Args:
        protocol: Optional protocol name (e.g. ``"bgp"``, ``"quic"``).
            When provided, the returned path is narrowed to
            ``protocol-testing/<protocol>/`` and validated to exist.

    Returns:
        Absolute path to the protocol directory, or None if not found.
    """
    root, ws_root = _find_protocol_testing_root()
    if root is None:
        return None

    if protocol is not None:
        specific = os.path.join(root, protocol)
        return specific if os.path.isdir(specific) else None

    # Resolve protocol from active workspace state
    if ws_root:
        ws_protocol = resolve_protocol_from_workspace(ws_root)
        if ws_protocol:
            specific = os.path.join(root, ws_protocol)
            if os.path.isdir(specific):
                return specific

    # Scan subdirs for any with an active-workflow file
    try:
        for name in sorted(os.listdir(root)):
            subdir = os.path.join(root, name)
            if os.path.isdir(subdir) and not name.startswith("."):
                state = os.path.join(subdir, _STATE_DIR_NAME, _ACTIVE_WORKFLOW_FILE)
                if os.path.isfile(state):
                    return subdir
    except OSError:
        pass

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


def append_journal_event(
    protocol_dir: str,
    event_type: str,
    payload: dict,
    workflow: str | None,
    phase: str | None,
) -> bool:
    """Append a single event to the workflow journal.

    Args:
        protocol_dir: Path to the protocol directory.
        event_type: One of the valid event types.
        payload: Type-specific event data.
        workflow: Current workflow name (can be None for pre-activation events).
        phase: Current phase (can be None).

    Returns:
        True if the event was appended, False if the event type is invalid.
    """
    if event_type not in _VALID_EVENT_TYPES:
        return False

    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)

    journal_path = state_path / _JOURNAL_FILE
    entries: list[dict] = []
    if journal_path.exists():
        try:
            with open(journal_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    entries = loaded
        except (OSError, yaml.YAMLError):
            pass

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "workflow": workflow,
        "phase": phase,
        "payload": payload,
    }
    entries.append(entry)

    with open(journal_path, "w") as f:
        yaml.safe_dump(entries, f, default_flow_style=False)

    return True


def get_journal_entries(protocol_dir: str, last_n: int = 20) -> list[dict]:
    """Read the last N entries from the workflow journal.

    Args:
        protocol_dir: Path to the protocol directory.
        last_n: Number of recent entries to return.

    Returns:
        List of journal entry dicts, newest last.
    """
    journal_path = _state_dir(protocol_dir) / _JOURNAL_FILE
    if not journal_path.exists():
        return []
    try:
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
            if not isinstance(entries, list):
                return []
            return entries[-last_n:] if last_n < len(entries) else entries
    except (OSError, yaml.YAMLError):
        return []


def rotate_journal(protocol_dir: str, max_entries: int = 200) -> None:
    """Archive oldest entries when journal exceeds max_entries.

    Moves the oldest half to ``journal-archive/YYYY-MM-DD.yaml``.

    Args:
        protocol_dir: Path to the protocol directory.
        max_entries: Threshold to trigger rotation.
    """
    journal_path = _state_dir(protocol_dir) / _JOURNAL_FILE
    if not journal_path.exists():
        return

    try:
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
            if not isinstance(entries, list) or len(entries) <= max_entries:
                return
    except (OSError, yaml.YAMLError):
        return

    split_at = len(entries) // 2
    archive_entries = entries[:split_at]
    keep_entries = entries[split_at:]

    archive_dir = _state_dir(protocol_dir) / _JOURNAL_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".yaml"
    archive_path = archive_dir / archive_name

    existing_archive: list[dict] = []
    if archive_path.exists():
        try:
            with open(archive_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    existing_archive = loaded
        except (OSError, yaml.YAMLError):
            pass

    with open(archive_path, "w") as f:
        yaml.safe_dump(existing_archive + archive_entries, f, default_flow_style=False)

    with open(journal_path, "w") as f:
        yaml.safe_dump(keep_entries, f, default_flow_style=False)
