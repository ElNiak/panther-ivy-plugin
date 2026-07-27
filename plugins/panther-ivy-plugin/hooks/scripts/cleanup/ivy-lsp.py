#!/usr/bin/env python3
"""SessionEnd hook: kill all ivy_lsp processes tracked via PID files,
delete sidecar port files, and remove the MCP health state file.

Always returns 0 — cleanup hooks must never fail the session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output, is_pid_alive, read_pid_file  # noqa: E402

_PID_DIR = Path("/tmp/ivy-lsp-pids")
_HEALTH_STATE_FILE = Path("/tmp/ivy-mcp-health-state.json")


def main() -> None:
    terminated: list[int] = []

    if _PID_DIR.is_dir():
        for pidfile in sorted(_PID_DIR.glob("*.pid")):
            pid = read_pid_file(pidfile)
            if pid is not None and is_pid_alive(pid):
                try:
                    os.kill(pid, 15)  # SIGTERM
                    terminated.append(pid)
                except (OSError, ProcessLookupError):
                    pass
            try:
                pidfile.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    # Stale sidecar port files
    for portfile in Path("/tmp").glob("ivy-mcp-*.port"):
        try:
            portfile.unlink()
        except OSError:
            pass

    # Health state file
    try:
        _HEALTH_STATE_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass

    if terminated:
        message = f"[ivy-cleanup] LSP processes terminated (PIDs: {', '.join(str(p) for p in terminated)})"
    else:
        message = "[ivy-cleanup] LSP processes terminated"

    emit_hook_output("SessionEnd", system_message=message)


if __name__ == "__main__":
    main()
