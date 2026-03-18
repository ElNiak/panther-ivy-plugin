#!/usr/bin/env python3
"""PreToolUse hook: surface recent LSP errors before MCP tool calls.

Reads the last 50 lines of /tmp/ivy-lsp.log and filters for CRITICAL,
ERROR, or Traceback entries from the last 60 seconds. If found, returns
a warning in the hook response so the user sees it.
"""

import json
import os
import time
from collections import deque

LOG_PATH = os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp.log")
MAX_LINES = 50
MAX_AGE_SECONDS = 60
ERROR_PATTERNS = ("CRITICAL", "ERROR", "Traceback")
_ALLOW = json.dumps({"decision": "allow"})


def main():
    if not os.path.isfile(LOG_PATH):
        print(_ALLOW)
        return

    # Check mtime before reading the file to avoid unnecessary I/O
    try:
        log_mtime = os.path.getmtime(LOG_PATH)
    except OSError:
        print(_ALLOW)
        return

    if time.time() - log_mtime > MAX_AGE_SECONDS:
        print(_ALLOW)
        return

    try:
        with open(LOG_PATH, "r", errors="replace") as f:
            tail = deque(f, maxlen=MAX_LINES)
    except OSError:
        print(_ALLOW)
        return

    recent_errors = []
    for line in tail:
        line = line.rstrip()
        if any(pat in line for pat in ERROR_PATTERNS):
            recent_errors.append(line[:200])

    if not recent_errors:
        print(_ALLOW)
        return

    warning_text = "WARNING: Recent LSP errors detected in {}:\n{}".format(
        LOG_PATH,
        "\n".join(f"  {e}" for e in recent_errors[-5:]),  # last 5
    )
    print(json.dumps({"decision": "allow", "message": warning_text}))


if __name__ == "__main__":
    main()
