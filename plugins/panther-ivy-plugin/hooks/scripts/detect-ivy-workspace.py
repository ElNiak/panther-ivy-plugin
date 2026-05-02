#!/usr/bin/env python3
"""SessionStart hook: detect Ivy workspace and inject context for Claude.

Replaces ``detect-ivy-workspace.sh``. Subsumes the bash predecessor's
behavior:

  * Walk up from cwd looking for a PANTHER project root (containing
    ``panther/plugins/services/testers/panther_ivy/protocol-testing/``)
    or a standalone Ivy workspace (≥3 ``*.ivy`` files near the cwd).
  * Resolve a Claude session id from stdin payload + env vars and stamp
    it with a date prefix for chronological sorting.
  * Write workspace + log + session env vars to ``CLAUDE_ENV_FILE`` for
    consumption by later hooks.
  * Persist a per-workspace session-id file under ``/tmp`` so MCP server
    launchers can recover it via the workspace path hash.
  * Prune session directories older than 7 days under
    ``${IVY_WORKSPACE_ROOT}/.observability/sessions``.
  * Detect MCP server status from the MCP log.
  * Restore an active workspace from ``.ivy-workspace-state.json`` if set.
  * Seed the statusline cache with workspace + MCP sections.
  * Emit a single SessionStart envelope with a slim ``systemMessage`` and
    a verbose ``additionalContext`` describing the detected workspace.

Detection delegates to the canonical implementation in
``ivy_lsp.core.workspace.detection`` when importable; otherwise it falls
back to ``hook_utils.get_workspace_root`` (which mirrors the bash
walk-up algorithm).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import (  # noqa: E402
    emit_hook_output,
    get_workspace_root as _hook_utils_workspace_root,
    read_stdin,
    resolve_session_id,
    resolve_workspace_state_path,
)
from statusline_cache import update_from_hook as _statusline_update  # noqa: E402


# ---------------------------------------------------------------------------
# ivy_lsp detection (delegated; falls back to hook_utils walk-up)
# ---------------------------------------------------------------------------


def _add_ivy_lsp_to_sys_path() -> None:
    """Mirror ``workspace-common.sh::resolve_ivy_lsp_source``.

    Priority: ``IVY_LSP_DEV_ROOT`` > local submodule reachable from cwd >
    no addition (rely on whatever Python already has on ``sys.path``).
    """
    dev_root = os.environ.get("IVY_LSP_DEV_ROOT", "").strip()
    if dev_root and (Path(dev_root) / "ivy_lsp").is_dir():
        if dev_root not in sys.path:
            sys.path.insert(0, dev_root)
        return

    candidates = (
        "panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp",
        "submodules/ivy-lsp",
    )
    check = Path.cwd()
    for _ in range(10):
        for candidate in candidates:
            local = check / candidate
            if (local / "ivy_lsp").is_dir():
                if str(local) not in sys.path:
                    sys.path.insert(0, str(local))
                return
        if check.parent == check:
            return
        check = check.parent


def _detect_via_ivy_lsp(cwd: Path) -> tuple[str, str] | None:
    """Try the canonical workspace detection. Return ``(root, type)`` or None.

    Mirrors the bash predecessor's ``python3 -m ivy_lsp detect "$PWD"`` code
    path: invokes ``WorkspaceContext.detect(start_dir)`` which returns a
    JSON-serializable dict with ``workspace_root`` and ``project_type``
    keys. Falls back to None on import failure (ivy_lsp not on sys.path)
    or on detection-time errors that the caller's fallback path can
    handle (OSError walking the filesystem, ValueError on malformed
    `.ivyworkspace`).
    """
    _add_ivy_lsp_to_sys_path()
    try:
        from ivy_lsp.core.workspace.context import WorkspaceContext  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        result = WorkspaceContext.detect(str(cwd))
    except (OSError, ValueError, KeyError):
        return None
    root = result.get("workspace_root")
    if not root:
        return None
    return str(root), str(result.get("project_type") or "fallback")


def _detect_via_hook_utils(cwd: Path) -> tuple[str, str]:
    """Fallback detection via ``hook_utils.get_workspace_root``."""
    root = _hook_utils_workspace_root()
    if Path(root, "protocol-testing").is_dir():
        return root, "panther"
    # Standalone heuristic: any directory near cwd with ≥3 .ivy files.
    check = cwd
    for _ in range(8):
        try:
            ivy_count = sum(
                1
                for _ in check.glob("*.ivy")
            ) + sum(1 for _ in check.glob("*/*.ivy"))
        except OSError:
            ivy_count = 0
        if ivy_count >= 3:
            return str(check), "standalone"
        if check.parent == check:
            break
        check = check.parent
    return str(cwd.resolve()), "fallback"


def _detect_workspace(cwd: Path) -> tuple[str, str]:
    via_lsp = _detect_via_ivy_lsp(cwd)
    if via_lsp is not None:
        return via_lsp
    return _detect_via_hook_utils(cwd)


# ---------------------------------------------------------------------------
# Session id + observability cleanup
# ---------------------------------------------------------------------------


def _stamped_session_id(hook_input: dict[str, Any]) -> str:
    """Return a date-prefixed session id (matches bash behavior)."""
    base = resolve_session_id(hook_input)
    if not base or base == "unknown":
        return ""
    stamp = time.strftime("%Y-%m-%dT%H%M")
    return f"{stamp}-{base}"


def _prune_old_sessions(workspace_root: Path, days: int = 7) -> None:
    """Remove session directories older than ``days`` days."""
    sessions = workspace_root / ".observability" / "sessions"
    if not sessions.is_dir():
        return
    cutoff = time.time() - days * 86400
    for child in sessions.iterdir():
        if not child.is_dir():
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue


# ---------------------------------------------------------------------------
# CLAUDE_ENV_FILE writes
# ---------------------------------------------------------------------------


def _append_env_file(updates: dict[str, str]) -> None:
    target = os.environ.get("CLAUDE_ENV_FILE", "").strip()
    if not target:
        return
    try:
        with open(target, "a") as f:
            for key, value in updates.items():
                f.write(f'{key}="{value}"\n')
    except OSError:
        pass


def _write_session_id_files(detected_root: str, session_id: str) -> None:
    """Persist the session id under /tmp keyed by sha256 of the workspace path.

    Writes one file for the detected root and (if different) one for the
    panther_ivy submodule root, mirroring the bash hash logic.
    """
    if not session_id:
        return
    paths_to_hash = {detected_root}
    panther_ivy = _hook_utils_workspace_root()
    if panther_ivy and panther_ivy != detected_root:
        paths_to_hash.add(panther_ivy)
    for path in paths_to_hash:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        try:
            Path(f"/tmp/ivy-session-{digest}.id").write_text(f"{session_id}\n")
        except OSError:
            continue


# ---------------------------------------------------------------------------
# MCP status + active workspace state
# ---------------------------------------------------------------------------


def _mcp_status(mcp_log: Path) -> str:
    if not mcp_log.is_file():
        return "not started"
    try:
        with open(mcp_log, "r", errors="replace") as f:
            for line in f:
                if "[MCP-READY]" in line:
                    return "ready"
    except OSError:
        return "starting"
    return "starting"


def _active_workspace(detected_root: Path) -> tuple[str, str]:
    """Return (active_group, set_by) from .ivy-workspace-state.json. Empty if none.

    Delegates path resolution to ``hook_utils.resolve_workspace_state_path``
    so that the banner finds state files written by the MCP tool at the
    panther_ivy submodule root even when ``detected_root`` resolves to
    the PANTHER project root above it.
    """
    state_file = resolve_workspace_state_path(detected_root)
    if state_file is None:
        return "", ""
    try:
        data = json.loads(Path(state_file).read_text())
    except (OSError, json.JSONDecodeError):
        return "", ""
    return str(data.get("active_group", "")), str(data.get("set_by", ""))


# ---------------------------------------------------------------------------
# Statusline cache
# ---------------------------------------------------------------------------


def _seed_statusline(
    detected_root: str,
    detected_type: str,
    active_group: str,
    mcp_status_text: str,
) -> None:
    if detected_type != "panther":
        return
    cache_status = {
        "ready": "up",
        "starting": "starting",
        "not started": "down",
    }.get(mcp_status_text, "unknown")
    sections = {
        "workspace": {
            "root": detected_root,
            "protocol": active_group,
            "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "mcp": {"status": cache_status},
    }
    for section, data in sections.items():
        try:
            _statusline_update(section, data)
        except Exception:
            continue


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    hook_input = read_stdin()
    cwd = Path.cwd()

    detected_root, detected_type = _detect_workspace(cwd)
    detected_path = Path(detected_root)
    session_id = _stamped_session_id(hook_input)

    mcp_log = Path(os.environ.get("IVY_MCP_LOG_PATH", "/tmp/ivy-mcp-latest.log"))
    lsp_log = Path(os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp-lsp-latest.log"))
    lsp_log_dir = lsp_log.parent if lsp_log.parent.exists() else Path("/tmp")

    env_updates: dict[str, str] = {
        "IVY_WORKSPACE_ROOT": detected_root,
        "IVY_LSP_LOG_PATH": str(lsp_log_dir / "ivy-lsp-lsp-latest.log"),
        "IVY_MCP_LOG_PATH": str(lsp_log_dir / "ivy-mcp-latest.log"),
        "IVY_MCP_PID_FILE": f"/tmp/ivy-mcp-{os.getpid()}.pid",
    }
    if session_id:
        env_updates["IVY_SESSION_ID"] = session_id

    active_group, set_by = _active_workspace(detected_path)
    if active_group and set_by == "explicit":
        env_updates["IVY_ACTIVE_WORKSPACE"] = active_group

    _append_env_file(env_updates)
    _write_session_id_files(detected_root, session_id)
    _prune_old_sessions(detected_path)

    mcp_status_text = _mcp_status(mcp_log)
    model_info = ""
    if detected_type == "panther":
        proto = detected_path / "protocol-testing"
        if proto.is_dir():
            try:
                ivy_count = sum(1 for _ in proto.rglob("*.ivy"))
            except OSError:
                ivy_count = 0
            model_info = f" | Models: {ivy_count} .ivy files"

    if detected_type == "panther":
        context = (
            f"[ivy-workspace] Detected PANTHER project at: {detected_root}. "
            "Ivy models are in protocol-testing/. The ivy-tools MCP server "
            "and LSP are scoped to this directory. "
            f"MCP: {mcp_status_text}{model_info}."
        )
    elif detected_type == "standalone":
        context = (
            f"[ivy-workspace] Detected standalone Ivy project at: "
            f"{detected_root}. MCP: {mcp_status_text}."
        )
    else:
        context = (
            f"[ivy-workspace] No Ivy project detected. "
            f"Using CWD as workspace: {detected_root}."
        )

    if active_group and set_by == "explicit":
        context += (
            f" Active workspace restored: {active_group} (set by: {set_by}). "
            "Use /set-workspace to change or /clear-workspace to remove "
            "restrictions."
        )
    else:
        context += (
            " No active workspace set. Use /set-workspace <protocol> to "
            "restrict edits. Available: quic, apt, apt_quic, minip, bgp, "
            "coap, scaffolds"
        )

    status_protocol = active_group or "none"
    env_file_target = os.environ.get("CLAUDE_ENV_FILE", "").strip()
    env_suffix = f" Env file: {env_file_target}." if env_file_target else ""
    status_line = (
        f"[ivy-workspace] detected: {detected_root}. Active workspace: "
        f"{status_protocol}.{env_suffix} Invoke /panther-ivy-plugin:ivy "
        "or describe your task in plain text."
    )

    _seed_statusline(detected_root, detected_type, active_group, mcp_status_text)

    emit_hook_output(
        "SessionStart",
        system_message=status_line,
        additional_context=context,
    )


if __name__ == "__main__":
    main()
