#!/usr/bin/env python3
"""SessionStart hook: remove PID files for dead processes; reap orphaned ivy_lsp.

Always returns 0 — cleanup hooks must never fail the session.
Phase 1: walk /tmp/ivy-lsp-pids/*.pid, drop entries whose PID is gone.
Phase 2: kill ivy_lsp processes whose command line points at the active
         workspace root but whose PID is not tracked by any PID file.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import emit_hook_output, emit_noop, is_pid_alive, read_pid_file  # noqa: E402

_PID_DIR = Path("/tmp/ivy-lsp-pids")
_DENY_COUNT_FILE = _PID_DIR / "indexing-deny-count"

_LATEST_LOG_SYMLINKS = (
    Path("/tmp/ivy-lsp-lsp-latest.log"),
    Path("/tmp/ivy-mcp-latest.log"),
)
# Filename format for per-PID logs is ``ivy-{lsp,mcp}-<ISO-timestamp>-<pid>.log``.
# We extract the trailing ``-<pid>.log`` to test the target's owning process.
_LOG_PID_RE = re.compile(r"-(\d+)\.log$")


def _clear_stale_log_symlinks() -> int:
    """Unlink ``/tmp/ivy-{lsp,mcp}-latest.log`` symlinks pointing to per-PID
    log files whose owning process is no longer alive.

    Without this, the next LSP / MCP startup may not refresh the symlink
    (the LSP only writes ``-latest.log`` on its own startup path), and a
    PreToolUse hook reading the symlink target sees content from a
    previous session — including the "Indexed N files" line that
    ``check-indexing-ready.py`` interprets as a fresh-Phase-1-finished
    signal. Unlinking forces the next live LSP startup to recreate the
    symlink correctly, and ``check-indexing-ready.py`` falls back to its
    other readiness signals while the symlink is absent.

    Returns the number of symlinks cleared. Safe no-op if symlinks don't
    exist or can't be parsed; cleanup hooks must never fail the session.
    """
    cleared = 0
    for symlink_path in _LATEST_LOG_SYMLINKS:
        if not symlink_path.is_symlink():
            continue
        try:
            target_basename = os.path.basename(os.readlink(symlink_path))
        except OSError:
            continue
        match = _LOG_PID_RE.search(target_basename)
        if not match:
            continue
        try:
            pid = int(match.group(1))
        except ValueError:
            continue
        if is_pid_alive(pid):
            continue
        try:
            symlink_path.unlink()
            cleared += 1
        except OSError:
            pass
    return cleared


def _clear_dead_pidfiles() -> tuple[int, list[int]]:
    """Remove PID files whose PID is dead. Returns (cleared, surviving_pids)."""
    cleared = 0
    survivors: list[int] = []
    for pidfile in sorted(_PID_DIR.glob("*.pid")):
        pid = read_pid_file(pidfile)
        if pid is None:
            continue
        if is_pid_alive(pid):
            survivors.append(pid)
            continue
        try:
            pidfile.unlink()
            cleared += 1
        except OSError:
            pass
    return cleared, survivors


def _resolve_workspace_root() -> str | None:
    """Best-effort workspace root — env vars only.

    `detect-ivy-workspace.py` runs earlier in the SessionStart chain and
    populates IVY_WORKSPACE_ROOT via CLAUDE_ENV_FILE. Without that, we
    silently skip Phase 2 (orphan kill) — Phase 1 still runs.
    """
    for var in ("IVY_WORKSPACE_ROOT", "IVY_LSP_WORKSPACE"):
        value = os.environ.get(var, "").strip()
        if value:
            return value
    return None


def _kill_orphans(workspace_root: str, tracked: list[int]) -> int:
    """Kill ivy_lsp processes pointing at workspace_root that are not tracked.

    Returns the number of orphans killed (used only for the system message;
    the bash original intentionally did not surface it).
    """
    own_pid = str(os.getpid())
    tracked_set = {str(p) for p in tracked}
    killed = 0
    try:
        ps = subprocess.run(
            ["ps", "-eo", "pid,args"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return 0

    for line in ps.stdout.splitlines():
        line = line.strip()
        if "ivy_lsp" not in line or workspace_root not in line:
            continue
        pid_str = line.split(None, 1)[0]
        if pid_str in tracked_set or pid_str == own_pid:
            continue
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        sys.stderr.write(f"[cleanup-stale-pids] Killing orphaned ivy_lsp process: PID={pid}\n")
        try:
            os.kill(pid, 15)  # SIGTERM
            killed += 1
        except ProcessLookupError:
            # Process exited between liveness check and kill — benign race.
            pass
        except PermissionError as exc:
            sys.stderr.write(
                f"[cleanup-stale-pids] kill PID={pid} failed: {exc}\n"
            )
        except OSError as exc:
            sys.stderr.write(
                f"[cleanup-stale-pids] kill PID={pid} failed: {exc}\n"
            )
    return killed


def main() -> None:
    if not _PID_DIR.exists():
        try:
            _PID_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        emit_noop("SessionStart", "no PID directory yet (fresh session)")
        return

    cleared, survivors = _clear_dead_pidfiles()
    stale_symlinks = _clear_stale_log_symlinks()

    orphans_killed = 0
    workspace_root = _resolve_workspace_root()
    if workspace_root:
        orphans_killed = _kill_orphans(workspace_root, survivors)

    # Reset the indexing deny counter for the new session.
    try:
        _DENY_COUNT_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass

    if cleared > 0 or stale_symlinks > 0:
        parts = []
        if cleared > 0:
            parts.append(f"{cleared} stale PIDs cleared")
        if stale_symlinks > 0:
            parts.append(f"{stale_symlinks} stale log symlinks unlinked")
        if orphans_killed > 0:
            parts.append(f"{orphans_killed} orphans killed")
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-cleanup] {', '.join(parts)}",
        )
    else:
        emit_noop(
            "SessionStart",
            f"no stale PIDs ({len(survivors)} live, {orphans_killed} orphans killed)",
        )


if __name__ == "__main__":
    main()
