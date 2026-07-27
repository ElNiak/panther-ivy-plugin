"""Active-workflow YAML read/write helpers.

Provides get/set/clear/update/validate/stale helpers that operate on
``<protocol_dir>/.panther-ivy/active-workflow``.
"""

from collections.abc import Set as AbstractSet
from datetime import datetime, timezone
from pathlib import Path

import yaml

from lib.workflow_state.context import (
    _ACTIVE_WORKFLOW_FILE,
    _KNOWN_WORKFLOWS,
    _state_dir,
)


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
) -> None:
    """Write the active-workflow YAML file.

    Args:
        protocol_dir: Path to the protocol directory.
        workflow: Name of the active workflow.
        phase: Current phase within the workflow.
    """
    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "workflow": workflow,
        "phase": phase,
        "started": datetime.now(timezone.utc).isoformat(),
    }

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


def validate_active_workflow(
    protocol_dir: str,
    known_workflows: AbstractSet[str] | None = None,
) -> tuple[bool, str | None]:
    """Validate the ``active-workflow`` YAML file against the 3-field schema.

    MCP-surfacing status (2026-04-23): this helper is called by in-process
    Python consumers (tests, hooks, future CLI tooling). Navigate's Phase 1
    Step 0 consumer described in the S8 spec is currently deferred — it
    requires adding ``ivy_workflow_state(action="validate")`` in the
    ivy-lsp submodule so a SKILL.md body can invoke validation via MCP.
    Until that lands, navigate relies on :func:`get_active_workflow`'s
    silent-None-on-corruption behavior; downstream reads that hit corrupt
    state surface the failure indirectly.


    Reads ``<protocol_dir>/.panther-ivy/active-workflow`` and checks:

    - File is valid YAML (``yaml.safe_load`` succeeds and yields a dict).
    - ``workflow`` is a non-empty string in the ``known_workflows`` set.
    - ``phase`` is a non-empty string.
    - ``started`` parses as ISO-8601.

    Args:
        protocol_dir: Path to the protocol directory.
        known_workflows: Optional set of accepted workflow names. When None,
            defaults to :data:`_KNOWN_WORKFLOWS` — the post-Phase-C canonical
            set of workflow names hardcoded in this module. The workflow-name
            check is skipped when the resolved set is empty.

    Returns:
        (True, None) if the file is absent (absence is valid; no active
            workflow is a normal state) or present and well-formed.
        (False, reason) if the file is malformed. ``reason`` is a
            human-readable short explanation suitable for surfacing to the
            user via AskUserQuestion.
    """
    path = _state_dir(protocol_dir) / _ACTIVE_WORKFLOW_FILE
    if not path.exists():
        return True, None

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except OSError as exc:
        return False, f"could not read active-workflow file: {exc}"
    except yaml.YAMLError as exc:
        return False, f"YAML parse error: {exc}"

    if not isinstance(data, dict):
        return False, f"expected a YAML dict, got {type(data).__name__}"

    workflow = data.get("workflow")
    if not isinstance(workflow, str) or not workflow:
        return False, "missing or empty 'workflow' field"

    if known_workflows is None:
        known_workflows = _KNOWN_WORKFLOWS
    if known_workflows and workflow not in known_workflows:
        reason = f"unknown workflow '{workflow}' (expected one of {sorted(known_workflows)})"
        return False, reason

    phase = data.get("phase")
    if not isinstance(phase, str) or not phase:
        return False, "missing or empty 'phase' field"

    started = data.get("started")
    if not isinstance(started, str) or not started:
        return False, "missing or empty 'started' field"
    try:
        datetime.fromisoformat(started)
    except (TypeError, ValueError):
        return False, f"'started' is not a valid ISO-8601 timestamp: {started!r}"

    return True, None


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
