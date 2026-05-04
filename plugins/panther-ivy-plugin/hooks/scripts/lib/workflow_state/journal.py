"""Journal read/write helpers.

``append_journal_event``, ``rotate_journal``, and ``append_pending_dispatch``
are co-located here per journaling-contract.md §4.2 sequential-write
assumption: keeping the read-modify-write operations in one module keeps
the locking window minimal and obvious.
"""

from datetime import datetime, timezone
from pathlib import Path

import yaml

from lib.workflow_state.context import (
    _JOURNAL_ARCHIVE_DIR,
    _JOURNAL_FILE,
    _VALID_EVENT_TYPES,
    _state_dir,
)


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
        target_workflow: The workflow that should run next (e.g. ``"refine"``).
        phase_hint: Optional phase to start the target in. When absent the
            target starts at its own ``init`` phase.
        reason: Human-readable reason for the dispatch (surfaced by
            ``/nct-observability``).

    Returns:
        True if the event was appended, False if event-type validation
        rejected the entry.
    """
    from lib.workflow_state.active import get_active_workflow
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
