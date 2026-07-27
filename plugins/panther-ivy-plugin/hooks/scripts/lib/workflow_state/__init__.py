"""Public API re-exports for lib.workflow_state.

Import from this package instead of the sub-modules. Underscore-prefixed
symbols are re-exported intentionally — tests/test_event_types_parity.py
and tests/test_workflow_context.py import them.
"""

from lib.workflow_state.context import (
    OPS_SKILLS,
    STATE_DIR_NAME,
    WorkflowContext,
    _KNOWN_WORKFLOWS,
    _VALID_EVENT_TYPES,
    active_workflow_path,
    find_protocol_dir,
    journal_path,
    journal_path_template,
    resolve_protocol_from_workspace,
)
from lib.workflow_state.active import (
    clear_active_workflow,
    get_active_workflow,
    is_workflow_stale,
    set_active_workflow,
    update_workflow_phase,
    validate_active_workflow,
)
from lib.workflow_state.journal import (
    append_journal_event,
    append_pending_dispatch,
    get_journal_entries,
    rotate_journal,
)
from lib.workflow_state.scaffold import (
    ScaffoldStateParseError,
    get_scaffold_state,
    get_scaffold_state_safe,
    set_scaffold_state,
)

__all__ = [
    # context
    "OPS_SKILLS",
    "STATE_DIR_NAME",
    "WorkflowContext",
    "_KNOWN_WORKFLOWS",
    "_VALID_EVENT_TYPES",
    "active_workflow_path",
    "find_protocol_dir",
    "journal_path",
    "journal_path_template",
    "resolve_protocol_from_workspace",
    # active
    "clear_active_workflow",
    "get_active_workflow",
    "is_workflow_stale",
    "set_active_workflow",
    "update_workflow_phase",
    "validate_active_workflow",
    # journal
    "append_journal_event",
    "append_pending_dispatch",
    "get_journal_entries",
    "rotate_journal",
    # scaffold
    "ScaffoldStateParseError",
    "get_scaffold_state",
    "get_scaffold_state_safe",
    "set_scaffold_state",
]
