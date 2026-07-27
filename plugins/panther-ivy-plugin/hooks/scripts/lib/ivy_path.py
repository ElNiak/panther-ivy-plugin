"""Helpers for validating .ivy file paths from tool_input dictionaries."""
from pathlib import Path
from typing import Optional


def resolve_ivy_path(tool_input: dict, event: str = "PostToolUse") -> Optional[Path]:
    """Return a Path for the tool_input's .ivy file, or None on no-op.

    Emits the appropriate emit_noop and returns None if:
    - tool_input has no file_path or empty file_path
    - the file_path does not end in .ivy
    - the path no longer exists on disk

    Args:
        tool_input: The tool_input subdict from the hook stdin payload.
        event: The Claude Code event name to pass to emit_noop (default "PostToolUse").

    Returns:
        Path object for the validated .ivy file, or None if any check fails
        (in which case emit_noop has already been called for the caller).
    """
    from lib.hook_utils import emit_noop  # local import to avoid cycle at module load
    raw = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
    if not raw or not raw.endswith(".ivy"):
        emit_noop(event, "non-.ivy file or empty path")
        return None
    p = Path(raw)
    if not p.is_file():
        emit_noop(event, f"file no longer exists: {p.name}")
        return None
    return p
