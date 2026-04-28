#!/usr/bin/env python3
"""PreToolUse hook: surface recent LSP errors before MCP tool calls.

Reads the last 50 lines of the MCP log and filters for CRITICAL,
ERROR, or Traceback entries from the last 60 seconds. Categorizes
errors and returns a structured summary.
"""

import json
import os
import time
from collections import deque

LOG_PATH = os.environ.get("IVY_MCP_LOG_PATH", "/tmp/ivy-mcp-latest.log")
MAX_LINES = 50
MAX_AGE_SECONDS = 60
ERROR_PATTERNS = ("CRITICAL", "ERROR", "Traceback")

# Category detection patterns
_CRASH_PATTERNS = ("Traceback", "CRITICAL", "FATAL", "segfault", "core dumped")
_TIMEOUT_PATTERNS = ("timed out", "timeout", "TimeoutError", "deadline exceeded")
_CONNECTION_PATTERNS = (
    "ConnectionRefused",
    "ConnectionReset",
    "BrokenPipe",
    "connection lost",
    "reconnect",
)


def _categorize(line: str) -> str:
    """Classify an error line into a category."""
    lower = line.lower()
    if any(p.lower() in lower for p in _CRASH_PATTERNS):
        return "crash"
    if any(p.lower() in lower for p in _TIMEOUT_PATTERNS):
        return "timeout"
    if any(p.lower() in lower for p in _CONNECTION_PATTERNS):
        return "connection"
    return "other"


def main():
    if not os.path.isfile(LOG_PATH):
        # No log file — silent pass
        exit(0)

    # Check mtime before reading the file to avoid unnecessary I/O
    try:
        log_mtime = os.path.getmtime(LOG_PATH)
    except OSError:
        exit(0)

    if time.time() - log_mtime > MAX_AGE_SECONDS:
        exit(0)

    try:
        with open(LOG_PATH, "r", errors="replace") as f:
            tail = deque(f, maxlen=MAX_LINES)
    except OSError:
        exit(0)

    recent_errors = []
    for line in tail:
        line = line.rstrip()
        if any(pat in line for pat in ERROR_PATTERNS):
            recent_errors.append(line[:200])

    if not recent_errors:
        exit(0)

    # Categorize errors
    counts = {"crash": 0, "timeout": 0, "connection": 0, "other": 0}
    for err in recent_errors:
        cat = _categorize(err)
        counts[cat] += 1

    most_recent = recent_errors[-1]

    parts = []
    parts.append(
        "Recent Ivy MCP errors (last 60s): "
        f"Crashes: {counts['crash']} | "
        f"Timeouts: {counts['timeout']} | "
        f"Connection: {counts['connection']} | "
        f"Other: {counts['other']}"
    )
    parts.append(f"  Most recent: {most_recent}")

    print(json.dumps({"systemMessage": "\n".join(parts)}))


if __name__ == "__main__":
    main()
