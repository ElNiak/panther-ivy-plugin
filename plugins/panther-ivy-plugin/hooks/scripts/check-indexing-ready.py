#!/usr/bin/env python3
"""PreToolUse hook: BLOCK MCP tools while ivy-lsp is still indexing.

Replaces ``check-indexing-ready.sh``. Uses ``permissionDecision: "deny"`` to
actually prevent the tool call when indexing is incomplete. After 6
consecutive denials (~60 s), degrades to a non-blocking advisory so the user
isn't trapped in a stuck-indexing loop.

Readiness protocol (consistent with wait-for-indexing):
  Signal 1: LSP log "Indexed N files"     — Phase 1 indexing complete
  Signal 2: Offline .ivy-index/ exists      — pre-built offline index
  Signal 3: MCP log "Pre-populated…"        — MCP prepopulation done
  Signal 4: MCP log "[MCP-READY]"           — MCP startup complete
  Any ONE signal allows the tool call.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import (  # noqa: E402
    emit_dedup,
    emit_hook_output,
    emit_noop,
    file_contains,
    is_pid_alive,
    read_stdin,
)
from statusline_cache import (  # noqa: E402
    _resolve_active_group,
    _resolve_workspace_root,
)
from statusline_cache import update_from_hook as _statusline_update  # noqa: E402


def _active_group() -> str | None:
    """Resolve the active ``ivy_workspace`` selection for partition routing.

    Returns the group from ``<workspace_root>/.ivy-workspace-state.json``
    so the ``lsp`` cache segment lands in the partition the renderer is
    reading. Returns ``None`` (which the cache layer maps to ``default``)
    when the workspace cannot be resolved or no selection is set. The
    underlying LSP server is workspace-shared but the rendered ``lsp``
    segment is per-protocol; a brief flicker on ``ivy_workspace`` switches
    is expected — the next ready probe re-populates the new partition.
    """
    ws = _resolve_workspace_root()
    return _resolve_active_group(ws) if ws else None

_MCP_LOG = Path(os.environ.get("IVY_MCP_LOG_PATH", "/tmp/ivy-mcp-latest.log"))
_LSP_LOG = Path(os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp-lsp-latest.log"))
_WORKSPACE_ROOT = os.environ.get("IVY_WORKSPACE_ROOT", "")

# Filename format for per-PID logs is ``ivy-{lsp,mcp}-<ISO-timestamp>-<pid>.log``.
# Mirrors the regex in ``cleanup-stale-pids.py``; kept duplicated rather than
# extracted to ``hook_utils`` because both call sites are tiny and adding a
# shared constant for one line of regex would be premature abstraction.
_LOG_PID_RE = re.compile(r"-(\d+)\.log$")

_DENY_STATE = Path("/tmp/ivy-lsp-pids/indexing-deny-count")
_DENY_THRESHOLD = 6
_STARTING_GRACE_S = 30
_INDEXING_GRACE_S = 120

# Above this age, the LSP log is treated as a leftover from a previous
# session whose process was SIGTERM'd or crashed without refreshing the
# `/tmp/ivy-lsp-lsp-latest.log` symlink. The "Indexed N files" line in such
# a log refers to the dead session's index and must NOT trigger a
# `[ivy-ready]` emission for the current session. 6 h is the upper bound on
# a normal active Claude Code session — sessions that legitimately last
# longer will see the SessionStart hook re-run on resume and clear the
# symlink first (see ``cleanup-stale-pids.py``).
_LSP_LOG_STALE_THRESHOLD_S = 6 * 3600


def _file_age_seconds(path: Path) -> float:
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return float("inf")


def _increment_deny() -> int:
    try:
        current = int(_DENY_STATE.read_text().strip()) if _DENY_STATE.exists() else 0
    except (OSError, ValueError):
        current = 0
    new = current + 1
    try:
        _DENY_STATE.parent.mkdir(parents=True, exist_ok=True)
        _DENY_STATE.write_text(str(new))
    except OSError as exc:
        sys.stderr.write(
            f"[ivy-indexing] deny-counter write failed at {_DENY_STATE}: {exc}\n"
        )
    return new


def _reset_deny() -> None:
    try:
        _DENY_STATE.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        sys.stderr.write(
            f"[ivy-indexing] deny-counter reset failed at {_DENY_STATE}: {exc}\n"
        )


def _emit_ready(reason: str, hook_input: dict | None = None) -> None:
    _reset_deny()
    _statusline_update("lsp", {"status": "ready"}, active_group=_active_group())
    emit_dedup(
        "PreToolUse",
        "ivy-ready",
        system_message=f"[ivy-ready] {reason}",
        hook_input=hook_input,
    )


def _signal_lsp_indexed() -> bool:
    """Signal 1: LSP log says ``Indexed <N> files`` AND the log is fresh.

    Two gates guard against the symlink-staleness scenario where
    ``/tmp/ivy-lsp-lsp-latest.log`` still points at a previous session's
    per-PID log file:

    1. **Mtime gate** — reject when the log hasn't been touched within
       ``_LSP_LOG_STALE_THRESHOLD_S`` (catches really-old leftovers).
    2. **PID-alive gate** — when the log is a symlink to ``…-<pid>.log``,
       extract the PID from the basename and reject when that process is
       no longer alive. This catches the more common case where some
       process keeps appending to the dead-LSP's log file (so the mtime
       still looks fresh) but the substring match would otherwise emit
       ``[ivy-ready]`` based on the dead session's "Indexed" line.

    See ``cleanup-stale-pids.py`` which unlinks dead-PID symlinks at
    SessionStart; the gates here are runtime defense-in-depth for the
    mid-session window when a fresh LSP crashes between calls.
    """
    if not _LSP_LOG.is_file():
        return False
    if _file_age_seconds(_LSP_LOG) > _LSP_LOG_STALE_THRESHOLD_S:
        return False
    if _LSP_LOG.is_symlink():
        try:
            target_basename = os.path.basename(os.readlink(_LSP_LOG))
            match = _LOG_PID_RE.search(target_basename)
            if match and not is_pid_alive(int(match.group(1))):
                return False
        except (OSError, ValueError):
            pass
    try:
        with open(_LSP_LOG, "r", errors="replace") as f:
            for line in f:
                if "Indexed " in line and " files" in line:
                    return True
    except OSError:
        return False
    return False


def _signal_offline_index() -> bool:
    """Signal 2: any ``protocol-testing/*/.ivy-index/manifest.json`` exists."""
    if not _WORKSPACE_ROOT:
        return False
    base = Path(_WORKSPACE_ROOT) / "protocol-testing"
    if not base.is_dir():
        return False
    return any((p / "manifest.json").is_file() for p in base.glob("*/.ivy-index"))


def _signal_mcp_prepopulated() -> bool:
    """Signal 3: MCP log mentions prepopulation completion."""
    return any(
        file_contains(_MCP_LOG, marker)
        for marker in ("Pre-populated from offline index", "pre-warmed", "PREWARM-DONE")
    )


def _signal_mcp_ready() -> bool:
    """Signal 4: MCP log carries the ``[MCP-READY]`` sentinel."""
    return file_contains(_MCP_LOG, "[MCP-READY]")


def main() -> None:
    hook_input = read_stdin()

    if _signal_lsp_indexed():
        _emit_ready("LSP Phase 1 indexing finished", hook_input=hook_input)
        return

    if _signal_offline_index():
        _emit_ready("offline index present", hook_input=hook_input)
        return

    if _signal_mcp_prepopulated():
        _emit_ready("MCP prepopulated from offline index", hook_input=hook_input)
        return

    if _signal_mcp_ready():
        _emit_ready("MCP-READY sentinel observed", hook_input=hook_input)
        return

    # --- Not ready: classify and surface ---
    mcp_started = file_contains(_MCP_LOG, "Starting ivy-lsp MCP server")
    if mcp_started:
        lsp_age = _file_age_seconds(_LSP_LOG) if _LSP_LOG.is_file() else float("inf")
        if lsp_age < _INDEXING_GRACE_S:
            deny_count = _increment_deny()
            if deny_count > _DENY_THRESHOLD:
                _statusline_update("lsp", {"status": "ready"}, active_group=_active_group())
                emit_hook_output(
                    "PreToolUse",
                    system_message=(
                        f"[ivy-indexing] allowing after {deny_count} denials "
                        f"(~{int(lsp_age)}s)"
                    ),
                    additional_context=(
                        f"[ivy-indexing] LSP indexing appears stuck "
                        f"(~{int(lsp_age)}s elapsed, {deny_count} denied calls). "
                        "Allowing tool call — results may be incomplete. "
                        "Consider running /nct-health."
                    ),
                )
                return

            _statusline_update("lsp", {"status": "indexing"}, active_group=_active_group())
            emit_hook_output(
                "PreToolUse",
                system_message=(
                    f"[ivy-indexing] not ready (attempt {deny_count}/{_DENY_THRESHOLD})"
                ),
                deny_reason=(
                    f"[ivy-indexing] LSP is still indexing the workspace "
                    f"(~{int(lsp_age)}s elapsed, attempt {deny_count}/{_DENY_THRESHOLD}). "
                    "Wait 10 seconds and retry."
                ),
                additional_context=(
                    "The LSP workspace index is not yet complete. Retry this "
                    "tool call after a short wait."
                ),
            )
            return

        # MCP up but LSP log absent or stale — assume ready, allow with hint.
        emit_hook_output(
            "PreToolUse",
            system_message="[ivy-health] MCP up, LSP log stale — allowing",
        )
        return

    mcp_age = _file_age_seconds(_MCP_LOG) if _MCP_LOG.is_file() else float("inf")
    if mcp_age < _STARTING_GRACE_S:
        emit_hook_output(
            "PreToolUse",
            system_message="[ivy-startup] MCP server starting",
            deny_reason=(
                f"[ivy-startup] MCP server is still starting up "
                f"(~{int(mcp_age)}s elapsed). Wait 10 seconds and retry."
            ),
            additional_context=(
                "The Ivy MCP server needs 5-15 seconds to initialize. "
                "Retry after a short wait."
            ),
        )
        return

    # No signal but past grace period — warn, allow.
    if not _MCP_LOG.is_file() and not _LSP_LOG.is_file():
        emit_noop("PreToolUse", "no MCP/LSP logs to evaluate readiness")
        return

    emit_hook_output(
        "PreToolUse",
        system_message="[ivy-health] MCP server status uncertain",
        additional_context=(
            "[ivy-health] MCP server may not be fully started. "
            "If this call fails, wait 10 seconds and retry."
        ),
    )


if __name__ == "__main__":
    main()
