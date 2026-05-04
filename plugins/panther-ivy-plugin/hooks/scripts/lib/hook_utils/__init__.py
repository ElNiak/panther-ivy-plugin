"""hook_utils package — re-exports the full public API.

Split layout:
  io.py       — stdin parsing, emit_hook_output, emit_noop, emit_dedup
  session.py  — session-ID resolution, activity flag, MCP health state
  workspace.py — workspace-root resolution, workspace state I/O
"""

from .io import (
    MAX_CONSECUTIVE_MCP_FAILURES,
    VALID_EVENT_NAMES,
    _EVENTS_WITH_HOOK_SPECIFIC_OUTPUT,
    _hook_dedup_cache_path,
    drain_warnings,
    emit_dedup,
    emit_hook_output,
    emit_noop,
    push_warning,
    read_stdin,
)
from .session import (
    _MCP_HEALTH_STATE_TTL,
    _session_activity_path,
    file_contains,
    get_mcp_health_state_path,
    is_pid_alive,
    is_session_active,
    mark_session_activity,
    read_mcp_health_state,
    read_pid_file,
    resolve_session_id,
    resolve_sessions_dir,
    write_mcp_health_state,
)
from .workspace import (
    get_workspace_root,
    read_active_workspace,
    resolve_active_group_for_hook,
    resolve_log_dir,
    resolve_workspace_state_path,
)

__all__ = [
    # io
    "MAX_CONSECUTIVE_MCP_FAILURES",
    "VALID_EVENT_NAMES",
    "drain_warnings",
    "emit_dedup",
    "emit_hook_output",
    "emit_noop",
    "push_warning",
    "read_stdin",
    # session
    "file_contains",
    "is_pid_alive",
    "is_session_active",
    "mark_session_activity",
    "read_mcp_health_state",
    "read_pid_file",
    "resolve_session_id",
    "resolve_sessions_dir",
    "write_mcp_health_state",
    # workspace
    "get_workspace_root",
    "read_active_workspace",
    "resolve_active_group_for_hook",
    "resolve_log_dir",
    "resolve_workspace_state_path",
]
