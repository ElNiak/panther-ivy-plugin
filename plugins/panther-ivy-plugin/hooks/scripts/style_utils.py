#!/usr/bin/env python3
"""Shared utilities for the workflow-aware output style system.

Loads style files (base, overlays, tool renderers, summaries) from the
``styles/`` directory under the plugin root, extracts markdown sections,
and composes the effective style document for injection via hooks.
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
    """Compose the effective style document from base + overlay + phase modifier.

    Args:
        plugin_root: Path to the plugin root directory.
        workflow: Active workflow name (e.g., "verify"), or None.
        phase: Active phase within the workflow (e.g., "compile"), or None.

    Returns:
        Composed markdown style document ready for injection.
    """
    parts: list[str] = []

    base = load_style_file(plugin_root, "base.md")
    if base:
        parts.append(base)

    if workflow:
        overlay = load_style_file(plugin_root, f"overlays/{workflow}.md")
        if overlay and phase:
            overlay = _highlight_active_phase(overlay, phase)
        if overlay:
            parts.append(overlay)

    return "\n\n---\n\n".join(parts) if parts else ""


def _highlight_active_phase(overlay: str, phase: str) -> str:
    """Mark the active phase section with [ACTIVE PHASE] in the overlay content."""
    pattern = re.compile(
        rf"^(###\s+{re.escape(phase)})\s*$",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1 [ACTIVE PHASE]", overlay)


def load_tool_renderer(
    plugin_root: str,
    tool_name: str,
    workflow: str | None,
) -> str | None:
    """Load the appropriate tool renderer section for the active workflow.

    Looks for a ``## {workflow}`` section in the renderer file. Falls back
    to ``## Default`` if the workflow section is not found. Returns None
    if the renderer file does not exist.
    """
    content = load_style_file(plugin_root, f"tool-renderers/{tool_name}.md")
    if content is None:
        return None

    if workflow:
        section = find_section(content, workflow)
        if section:
            return section

    default = find_section(content, "Default") or find_section(content, "Default (no workflow active)")
    return default


def load_summary_template(plugin_root: str, workflow: str | None) -> str | None:
    """Load the session summary template for the active workflow.

    Returns None if no template exists for the given workflow.
    """
    if not workflow:
        return None
    return load_style_file(plugin_root, f"summaries/{workflow}.md")


def resolve_plugin_root() -> str:
    """Resolve the plugin root directory.

    Uses CLAUDE_PLUGIN_ROOT env var if set, otherwise walks up from this
    file's location (hooks/scripts/ -> hooks/ -> plugin root).
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if env_root:
        return env_root
    return str(Path(__file__).resolve().parent.parent.parent)
