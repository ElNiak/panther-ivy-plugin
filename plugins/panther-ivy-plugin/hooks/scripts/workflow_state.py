#!/usr/bin/env python3
"""Read/write utilities for workflow state files.

State files live at ``<protocol_dir>/.panther-ivy/`` and track active
workflow context and multi-session build progress.
"""

import json
import os
import sys
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hook_utils import get_workspace_root

_STATE_DIR_NAME = ".panther-ivy"
_ACTIVE_WORKFLOW_FILE = "active-workflow"
_BUILD_STATE_FILE = "build-state.yaml"
_JOURNAL_FILE = "workflow-journal.yaml"
_JOURNAL_ARCHIVE_DIR = "journal-archive"

OPS_SKILLS = frozenset({
    "scaffold-ops",
    "verify-ops",
    "review-ops",
    "triage-ops",
    "meta-self-mod-ops",
})


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
    "pending_dispatch",
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


_WORKFLOW_CONTEXT_FIELDS = frozenset({"workflow", "phase", "started"})

_WARNED_UNKNOWN_FIELDS: set[str] = set()


@dataclass
class WorkflowContext:
    """Active workflow state plus the protocol directory it belongs to.

    The schema has three fields. Workflow composition is journaled via
    ``pending_dispatch`` events (see :func:`append_pending_dispatch`) rather
    than a caller/depth chain; every workflow returns to navigate on
    completion.

    Attributes:
        protocol_dir: Absolute path to the protocol directory (parent of
            ``.panther-ivy/``).
        workflow: Name of the active workflow (e.g. ``"scaffold"``, ``"verify"``).
        phase: Current phase within the workflow.
        started: ISO-8601 UTC timestamp when the workflow was set.
    """

    protocol_dir: str
    workflow: str
    phase: str | None = None
    started: str | None = None

    @classmethod
    def current(cls, protocol: str | None = None) -> "WorkflowContext | None":
        """Resolve the active workflow context.

        Args:
            protocol: Optional protocol name to narrow the search.

        Returns:
            A populated ``WorkflowContext`` when a protocol directory is
            found and its active-workflow file exists, else ``None``.
        """
        protocol_dir = find_protocol_dir(protocol)
        if protocol_dir is None:
            return None
        state = get_active_workflow(protocol_dir)
        if not state:
            return None
        filtered = {
            k: v for k, v in state.items() if k in _WORKFLOW_CONTEXT_FIELDS
        }
        unknown = set(state.keys()) - _WORKFLOW_CONTEXT_FIELDS
        new_unknown = unknown - _WARNED_UNKNOWN_FIELDS
        if new_unknown:
            print(
                f"WARN: WorkflowContext dropped unknown fields: {sorted(new_unknown)}",
                file=sys.stderr,
            )
            _WARNED_UNKNOWN_FIELDS.update(new_unknown)
        if "workflow" not in filtered:
            return None
        return cls(protocol_dir=protocol_dir, **filtered)


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


# Post-Phase-C canonical workflow names. routing-rules.json was archived in
# Phase D commit 01c9adf; the orchestrator at skills/ivy/SKILL.md and the
# specialised ops-skills (skills/{scaffold,verify,review,triage,meta}-ops plus
# the navigate flow inside the orchestrator) are the authoritative writers,
# all using the unprefixed names below.
_KNOWN_WORKFLOWS: frozenset[str] = frozenset({
    "navigate",
    "scaffold",
    "verify",
    "review",
    "triage",
    "meta",
})


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


class BuildStateParseError(Exception):
    """Raised when ``build-state.yaml`` exists but fails YAML parse.

    Distinguishes parse failure (file is present but corrupt — caller must
    handle / back up) from missing-file (benign — caller treats as a fresh
    build session).

    MCP-surfacing status (2026-04-23): SKILL.md workflow bodies call state
    ops via the ``ivy_workflow_state`` MCP tool, not via this Python module
    directly, so they cannot catch ``BuildStateParseError`` as an exception.
    Consuming this exception from navigate / build requires adding an MCP
    action in the ivy-lsp submodule (e.g. ``ivy_workflow_state(
    action="get_build")`` that distinguishes missing-file from parse-
    failure in its error surface). Until then this exception is consumed
    only by in-process Python callers: unit tests, hooks (via
    :func:`get_build_state_safe`), and future CLI tooling.
    """


def get_build_state(protocol_dir: str) -> dict | None:
    """Read ``<protocol_dir>/.panther-ivy/build-state.yaml``.

    Returns:
        None if the file does not exist.
        dict if the file parses successfully.

    Raises:
        BuildStateParseError: the file exists but YAML parse fails, or the
            parse yields a non-dict root. Includes the underlying parse
            error's message and the file path for caller diagnostics.
    """
    path = _state_dir(protocol_dir) / _BUILD_STATE_FILE
    if not path.exists():
        return None
    try:
        with open(path) as f:
            parsed = yaml.safe_load(f)
    except OSError as exc:
        raise BuildStateParseError(
            f"could not read build-state.yaml at {path}: {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        raise BuildStateParseError(
            f"YAML parse error in {path}: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise BuildStateParseError(
            f"expected a dict at {path} root, got {type(parsed).__name__}"
        )
    return parsed


def get_build_state_safe(protocol_dir: str) -> dict | None:
    """Hook-friendly wrapper: returns None on BOTH missing file and parse failure.

    Passive observers (hook scripts, status-line renderers) that want to
    continue gracefully when ``build-state.yaml`` is corrupt should call this
    wrapper instead of :func:`get_build_state`. Workflow bodies that own the
    file (build Phase 2 Step 2) should call :func:`get_build_state` directly
    and handle :class:`BuildStateParseError` with user-visible recovery.

    The parse failure is swallowed but reported once per process to
    ``sys.stderr`` so the user can investigate, without the hook itself
    raising.
    """
    try:
        return get_build_state(protocol_dir)
    except BuildStateParseError as exc:
        if "workflow_state" not in sys.modules or not getattr(
            sys.modules[__name__], "_BUILD_STATE_WARNED", False
        ):
            msg = f"WARN: get_build_state_safe swallowed parse failure at {protocol_dir}: {exc}"
            print(msg, file=sys.stderr)
            setattr(sys.modules[__name__], "_BUILD_STATE_WARNED", True)
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


def append_pending_dispatch(
    protocol_dir: str,
    target_workflow: str,
    phase_hint: str | None = None,
    reason: str | None = None,
) -> bool:
    """Append a ``pending_dispatch`` journal event signaling the next workflow.

    Workflows emit ``pending_dispatch`` immediately before clearing their own
    ``active-workflow`` flag to indicate which workflow navigate should
    activate next. Navigate consumes the event by writing a paired
    ``workflow_resumed`` entry and invoking the target skill.

    The emitting workflow's current ``workflow`` and ``phase`` (read from
    ``active-workflow``) are recorded on the journal entry's context fields;
    the target workflow travels in the payload.

    Args:
        protocol_dir: Path to the protocol directory.
        target_workflow: The workflow that should run next (e.g. ``"verify"``).
        phase_hint: Optional phase to start the target in. When absent the
            target starts at its own ``init`` phase.
        reason: Human-readable reason for the dispatch (surfaced by
            ``/nct-observability``).

    Returns:
        True if the event was appended, False if event-type validation
        rejected the entry.
    """
    current = get_active_workflow(protocol_dir)
    emitting_workflow = current.get("workflow") if current else None
    emitting_phase = current.get("phase") if current else None
    payload: dict = {"workflow": target_workflow}
    if phase_hint is not None:
        payload["phase_hint"] = phase_hint
    if reason is not None:
        payload["reason"] = reason
    return append_journal_event(
        protocol_dir,
        event_type="pending_dispatch",
        payload=payload,
        workflow=emitting_workflow,
        phase=emitting_phase,
    )


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
