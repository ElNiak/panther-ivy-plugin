#!/usr/bin/env python3
"""Shared utilities for the workflow-aware output style system.

Loads workflow overlay files from the ``styles/`` directory under the
plugin root, extracts markdown sections, and composes the overlay
document for injection via hooks. Base formatting conventions are
handled by output styles at the session level.
"""

import os
import re
from pathlib import Path


def find_section(content: str, heading: str, level: int = 2) -> str | None:
    """Extract a section from markdown content by its heading.

    Returns the text between the matched heading and the next heading of
    equal or higher level, stripped of leading/trailing whitespace.
    Returns None if the heading is not found.
    """
    prefix = "#" * level
    pattern = re.compile(
        rf"^{prefix}\s+{re.escape(heading)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return None

    start = match.end()
    # Find next heading of same or higher level
    next_heading = re.compile(rf"^#{{{1},{level}}}\s+", re.MULTILINE)
    end_match = next_heading.search(content, start)
    section = content[start : end_match.start()] if end_match else content[start:]
    return section.strip()


def load_style_file(plugin_root: str, relative_path: str) -> str | None:
    """Load a style file from ``{plugin_root}/styles/{relative_path}``.

    Returns the file content as a string, or None if the file does not exist.
    """
    path = Path(plugin_root) / "styles" / relative_path
    if not path.is_file():
        return None
    return path.read_text()


def compose_style(
    plugin_root: str,
    workflow: str | None,
    phase: str | None,
) -> str:
    """Compose the workflow overlay with active phase highlighted.

    Base formatting conventions are handled by output styles at the session
    level. This function only returns the workflow overlay when a workflow
    is active.

    Args:
        plugin_root: Path to the plugin root directory.
        workflow: Active workflow name (e.g., "verify"), or None.
        phase: Active phase within the workflow (e.g., "compile"), or None.

    Returns:
        Workflow overlay markdown, or empty string if no workflow active.
    """
    if not workflow:
        return ""

    overlay = load_style_file(plugin_root, f"overlays/{workflow}.md")
    if not overlay:
        return ""

    if phase:
        overlay = _highlight_active_phase(overlay, phase)

    return overlay


def _highlight_active_phase(overlay: str, phase: str) -> str:
    """Mark the active phase section with [ACTIVE PHASE] in the overlay content."""
    pattern = re.compile(
        rf"^(###\s+{re.escape(phase)})\s*$",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1 [ACTIVE PHASE]", overlay)


def resolve_plugin_root() -> str:
    """Resolve the plugin root directory.

    Uses CLAUDE_PLUGIN_ROOT env var if set, otherwise walks up from this
    file's location (hooks/scripts/ -> hooks/ -> plugin root).
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if env_root:
        return env_root
    return str(Path(__file__).resolve().parent.parent.parent)
