#!/usr/bin/env python3
"""Notification hook: detect MCP server disconnection and advise reconnection.

When Claude Code fires a Notification event for an MCP server disconnect,
this hook outputs additionalContext instructing Claude to suggest the user
run /mcp to reconnect.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from hook_utils import emit_hook_output, read_stdin

# Substrings that indicate an MCP server disconnection notification.
_DISCONNECT_SIGNALS = (
    "disconnected",
    "no longer available",
    "server crashed",
    "connection lost",
    "connection closed",
    "server stopped",
    "MCP server",
)

_IVY_SERVER_NAMES = ("ivy-tools", "ivy_tools", "panther-ivy", "serena")


def _is_ivy_mcp_disconnect(data: dict) -> bool:
    """Check if this notification is about an Ivy MCP server disconnecting."""
    message = str(data.get("message", "")).lower()
    title = str(data.get("title", "")).lower()
    notification_type = str(data.get("notification_type", "")).lower()
    combined = f"{title} {message} {notification_type}"

    has_disconnect_signal = any(sig in combined for sig in _DISCONNECT_SIGNALS)
    has_ivy_reference = any(name in combined for name in _IVY_SERVER_NAMES)

    # Also match generic MCP disconnect if it mentions "mcp" broadly
    has_mcp_reference = "mcp" in combined

    return has_disconnect_signal and (has_ivy_reference or has_mcp_reference)


def main():
    data = read_stdin()

    if not _is_ivy_mcp_disconnect(data):
        return

    emit_hook_output(
        "Notification",
        additional_context=(
            "[ivy-health] The Ivy MCP server has disconnected. "
            "Run /mcp to reconnect, or type 'reconnect mcp' to trigger "
            "a manual reconnection. MCP-dependent tools (ivy_verify, "
            "ivy_coverage, ivy_diagnostics, etc.) will not work until "
            "the server is back."
        ),
    )


if __name__ == "__main__":
    main()
