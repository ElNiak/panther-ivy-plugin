"""WorkflowContext dataclass, event-type constants, and path helpers.

Single source of truth for ``_VALID_EVENT_TYPES`` — parity-checked against
``ivy_lsp/mcp/tools/workflow_state.py`` by ``tests/test_event_types_parity.py``.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from hook_utils import emit_noop, get_workspace_root

STATE_DIR_NAME = ".panther-ivy"
_ACTIVE_WORKFLOW_FILE = "active-workflow"
_SCAFFOLD_STATE_FILE = "scaffold-state.yaml"
_JOURNAL_FILE = "workflow-journal.yaml"
_JOURNAL_ARCHIVE_DIR = "journal-archive"


def journal_path(protocol_dir: str) -> str:
    """Return the absolute path to the workflow journal for a protocol directory.

    Hooks following the T2 (``appended to journal at <path>``) template
    in ``output-style.md`` use this to cite the journal location in
    their ``system_message``. Centralising the path construction keeps
    every retrofit consistent and survives a future rename of the
    journal filename.

    Args:
        protocol_dir: Absolute path to the protocol directory whose
            ``.panther-ivy/`` subdirectory holds the workflow state files.

    Returns:
        Absolute path to ``<protocol_dir>/.panther-ivy/workflow-journal.yaml``.
        The file may not exist yet; callers cite the path regardless
        because it is the canonical location whether or not anything has
        been appended.
    """
    return os.path.join(protocol_dir, STATE_DIR_NAME, _JOURNAL_FILE)


def journal_path_template() -> str:
    """Return the canonical journal path string with a protocol placeholder.

    This helper exists for hook directives that need to reference the
    canonical journal location but do not have a concrete protocol
    directory at runtime.

    Returns:
        Canonical journal location expressed as
        ``<protocol_dir>/.panther-ivy/workflow-journal.yaml``.
    """
    return journal_path("<protocol_dir>")


def active_workflow_path(protocol_dir: str) -> str:
    """Return the absolute path to the active-workflow file for a protocol directory.

    Args:
        protocol_dir: Absolute path to the protocol directory whose
            ``.panther-ivy/`` subdirectory holds the workflow state files.

    Returns:
        Absolute path to ``<protocol_dir>/.panther-ivy/active-workflow``.
    """
    return os.path.join(protocol_dir, STATE_DIR_NAME, _ACTIVE_WORKFLOW_FILE)


OPS_SKILLS = frozenset({
    "scaffold-ops",
    "refine-ops",
    "experiment-ops",
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
    if ws_root := os.environ.get("IVY_WORKSPACE_ROOT", "").strip():
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
        if ws_protocol := resolve_protocol_from_workspace(ws_root):
            specific = os.path.join(root, ws_protocol)
            if os.path.isdir(specific):
                return specific

    # Scan subdirs for any with an active-workflow file
    try:
        for name in sorted(os.listdir(root)):
            subdir = os.path.join(root, name)
            if os.path.isdir(subdir) and not name.startswith("."):
                state = os.path.join(subdir, STATE_DIR_NAME, _ACTIVE_WORKFLOW_FILE)
                if os.path.isfile(state):
                    return subdir
    except OSError:
        emit_noop("WorkflowState", f"error scanning for protocol dirs in {root}")

    return root


def _state_dir(protocol_dir: str) -> Path:
    """Returns the ``.panther-ivy`` state directory inside *protocol_dir*."""
    return Path(protocol_dir) / STATE_DIR_NAME


_WORKFLOW_CONTEXT_FIELDS = frozenset({"workflow", "phase", "started"})

_WARNED_UNKNOWN_FIELDS: set[str] = set()


# Post-Phase-C canonical workflow names. routing-rules.json was archived in
# Phase D commit 01c9adf; the orchestrator at skills/ivy/SKILL.md and the
# specialised ops-skills (skills/{scaffold,refine,experiment,review,triage,meta}-ops
# plus the navigate flow inside the orchestrator) are the authoritative writers,
# all using the unprefixed names below.
_KNOWN_WORKFLOWS: frozenset[str] = frozenset({
    "navigate",
    "scaffold",
    "refine",
    "experiment",
    "review",
    "triage",
    "meta",
})


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
        workflow: Name of the active workflow (e.g. ``"scaffold"``, ``"refine"``).
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
        from lib.workflow_state.active import get_active_workflow
        state = get_active_workflow(protocol_dir)
        if not state:
            return None
        filtered = {
            k: v for k, v in state.items() if k in _WORKFLOW_CONTEXT_FIELDS
        }
        unknown = set(state.keys()) - _WORKFLOW_CONTEXT_FIELDS
        if new_unknown := unknown - _WARNED_UNKNOWN_FIELDS:
            emit_noop(
                "WorkflowState",
                f"WARN - active-workflow file at {protocol_dir} has unknown fields: {sorted(unknown)}",
            )
            _WARNED_UNKNOWN_FIELDS.update(new_unknown)
        if "workflow" not in filtered:
            return None
        return cls(protocol_dir=protocol_dir, **filtered)
