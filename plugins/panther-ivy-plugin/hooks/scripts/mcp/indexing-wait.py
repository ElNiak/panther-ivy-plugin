#!/usr/bin/env python3
"""SessionStart hook: wait for ivy-lsp MCP server to be ready.

Polls the MCP log for the ``[MCP-READY]`` sentinel logged after tool
registration completes; bails early on ``[MCP-FATAL]`` or a dead MCP PID.
After MCP is ready, waits up to 5 additional seconds for LSP indexing.
Surfaces a single status line (and a model-readiness hint) as
``additionalContext`` for Claude.

Replaces ``wait-for-indexing.sh``. The bash predecessor sourced
``statusline_update_helper.sh``; the Python rewrite calls
``statusline_cache.update_from_hook`` directly.

The harness can kill this hook with SIGTERM if it exceeds its hooks.json
timeout. The original bash version installed a ``trap`` handler that emitted
a partial-status envelope on TERM/INT; this Python version uses
``signal.signal(signal.SIGTERM, ...)`` for the same guarantee.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output, file_contains, is_pid_alive, read_pid_file  # noqa: E402
from lib.statusline_cache import update_from_hook as _statusline_update  # noqa: E402

_MCP_LOG = Path(os.environ.get("IVY_MCP_LOG_PATH", "/tmp/ivy-mcp-latest.log"))
_LSP_LOG = Path(os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp-lsp-latest.log"))
_MAX_WAIT_S = int(os.environ.get("IVY_LSP_INDEX_TIMEOUT", "12"))
_LSP_GRACE_S = 5

_START = time.monotonic()


def _last_line_with(path: Path, needle: str) -> str:
    last = ""
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                if needle in line:
                    last = line.rstrip()
    except OSError:
        return ""
    return last


def _mcp_pid_alive() -> tuple[bool, int | None]:
    """Return (any_pidfile_seen, dead_pid_if_any).

    True/None  → at least one MCP PID is live.
    True/<pid> → an MCP PID file exists but the process is dead.
    False/None → no MCP PID files (inconclusive).
    """
    pid_dir = Path("/tmp/ivy-lsp-pids")
    if not pid_dir.is_dir():
        return False, None
    any_seen = False
    for pidfile in pid_dir.glob("mcp-*.pid"):
        pid = read_pid_file(pidfile)
        if pid is None:
            continue
        any_seen = True
        if not is_pid_alive(pid):
            return any_seen, pid
    return any_seen, None


def _wait_for_mcp_ready() -> tuple[bool, str]:
    """Poll the MCP log for [MCP-READY]. Returns (ready, optional_error_msg)."""
    deadline = _START + _MAX_WAIT_S
    while time.monotonic() < deadline:
        if _MCP_LOG.is_file() and file_contains(_MCP_LOG, "[MCP-READY]"):
            return True, ""
        if _MCP_LOG.is_file() and file_contains(_MCP_LOG, "[MCP-FATAL]"):
            crash = _last_line_with(_MCP_LOG, "[MCP-FATAL]")
            return False, f"[ivy-indexing] MCP server CRASHED: {crash}"
        any_pidfile, dead_pid = _mcp_pid_alive()
        if any_pidfile and dead_pid is not None:
            return False, f"[ivy-indexing] MCP server process died (PID={dead_pid})"
        time.sleep(1)
    return False, ""


def _wait_for_lsp_indexed(after_mcp_ready: bool) -> tuple[bool, str]:
    """Best-effort wait for LSP `Indexed N files`. Returns (indexed, status_line)."""
    if not _LSP_LOG.is_file():
        return False, ""
    if after_mcp_ready:
        deadline = time.monotonic() + _LSP_GRACE_S
        while time.monotonic() < deadline:
            if file_contains(_LSP_LOG, "Indexed ") and file_contains(_LSP_LOG, " files"):
                return True, _last_line_with(_LSP_LOG, "Indexed ")
            time.sleep(1)
        return False, "still indexing"
    # MCP not ready: do a single non-blocking probe so the report is honest.
    if file_contains(_LSP_LOG, "Indexed ") and file_contains(_LSP_LOG, " files"):
        return True, _last_line_with(_LSP_LOG, "Indexed ")
    return False, ""


def _workspace_info() -> str:
    active = os.environ.get("IVY_ACTIVE_WORKSPACE", "").strip()
    if not active:
        return ""
    workspace_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if not workspace_root:
        return f" Active workspace: {active}."
    state_file = Path(workspace_root) / ".ivy-workspace-state.json"
    if not state_file.is_file():
        return f" Active workspace: {active}."
    try:
        proto_dir = Path(workspace_root) / "protocol-testing" / active
        ivy_count = sum(1 for _ in proto_dir.rglob("*.ivy"))
    except OSError:
        ivy_count = 0
    return f" Active workspace: {active} ({ivy_count} .ivy files)."


def _model_status() -> str:
    if not _MCP_LOG.is_file():
        return ""
    if file_contains(_MCP_LOG, "[INDEX-MODEL-READY]"):
        return "ready"
    if file_contains(_MCP_LOG, "[INDEX-PREWARM]"):
        return "building"
    return ""


def _emit_termination(_signum: int, _frame: Any) -> None:
    # Two envelopes on one stdout stream confuse the runtime parser; the
    # ``already_emitted`` attribute lets ``main()`` claim the slot before
    # the handler can produce its own.
    if not getattr(_emit_termination, "already_emitted", False):
        elapsed = int(time.monotonic() - _START)
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-indexing] timed out after {elapsed}s",
            additional_context=(
                "[ivy-indexing] Readiness check timed out. MCP tools may still "
                "be starting — retry after 10 seconds if a tool call fails."
            ),
        )
    sys.stdout.flush()
    sys.exit(0)


def _mark_emitted() -> None:
    sys.stdout.flush()
    _emit_termination.already_emitted = True  # type: ignore[attr-defined]


def main() -> None:
    signal.signal(signal.SIGTERM, _emit_termination)
    signal.signal(signal.SIGINT, _emit_termination)

    # Guard: skip polling entirely if no MCP log was configured AND the
    # default fallback file does not exist. Mirrors the bash early-skip.
    if "IVY_MCP_LOG_PATH" not in os.environ and not _MCP_LOG.is_file():
        emit_hook_output(
            "SessionStart",
            system_message="[ivy-indexing] skipped (MCP log unavailable)",
            additional_context=(
                "[ivy-indexing] MCP server log not available — skipping "
                "readiness check."
            ),
        )
        _mark_emitted()
        return

    mcp_ready, error_msg = _wait_for_mcp_ready()
    lsp_indexed, lsp_status = _wait_for_lsp_indexed(after_mcp_ready=mcp_ready)

    # Statusline cache updates.
    if mcp_ready:
        _statusline_update("mcp", {"status": "up"})
    else:
        _statusline_update("mcp", {"status": "down", "last_error": "startup-timeout"})
    if lsp_indexed:
        _statusline_update("lsp", {"status": "ready"})
    elif lsp_status == "still indexing":
        _statusline_update("lsp", {"status": "indexing"})

    elapsed = int(time.monotonic() - _START)
    workspace_info = _workspace_info()
    model_status = _model_status()

    if error_msg:
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-indexing] {('crashed' if 'CRASHED' in error_msg else 'died')} after {elapsed}s",
            additional_context=error_msg,
        )
        return

    if not mcp_ready:
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-indexing] timed out after {elapsed}s",
            additional_context=(
                f"[ivy-indexing] WARNING: MCP server did not start within "
                f"{_MAX_WAIT_S}s. If an ivy MCP tool call fails with a server "
                "error, wait 10 seconds and retry the same call up to 3 times "
                "before reporting failure to the user."
            ),
        )
        _mark_emitted()
        return

    base = "[ivy-indexing] MCP server ready."
    if model_status == "ready":
        model_msg = " Model: ready."
    elif model_status == "building":
        model_msg = " Model: building (will be ready for coverage/traceability tools shortly)."
    else:
        model_msg = " Model builds lazily on first tool call."

    if lsp_indexed and lsp_status:
        lsp_msg = f" LSP: {lsp_status}."
    elif lsp_status == "still indexing":
        lsp_msg = " LSP: still indexing. Wait 10 seconds for indexing to finish before calling MCP tools."
    else:
        lsp_msg = ""

    retry_hint = (
        " Note: If an ivy MCP tool fails unexpectedly, wait 5 seconds and "
        "retry once — the server may be recovering."
    )

    additional = base + model_msg + lsp_msg + workspace_info + retry_hint

    emit_hook_output(
        "SessionStart",
        system_message=f"[ivy-indexing] indexed ({elapsed}s)",
        additional_context=additional,
    )
    _mark_emitted()


if __name__ == "__main__":
    main()
