#!/usr/bin/env python3
"""PostToolUse hook for Skill: inject reference file content when skills with references/ are loaded."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin

_PLUGIN_PREFIX = "panther-ivy-plugin:"
_MAX_INLINE_LINES = 100


def _extract_skill_name(raw: str) -> str | None:
    """Extract skill name, stripping plugin prefix if present."""
    name = raw.strip().lower()
    if name.startswith(_PLUGIN_PREFIX):
        name = name[len(_PLUGIN_PREFIX):]
    return name if name else None


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Skill":
        return

    tool_input = hook_input.get("tool_input", {})
    skill_raw = tool_input.get("skill", "")
    skill_name = _extract_skill_name(skill_raw)
    if skill_name is None:
        return

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return

    refs_dir = Path(plugin_root) / "skills" / skill_name / "references"
    if not refs_dir.is_dir():
        return

    ref_files = sorted(refs_dir.glob("*.md"))
    if not ref_files:
        return

    parts = []
    read_paths = []

    for ref_file in ref_files:
        try:
            content = ref_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            if len(lines) <= _MAX_INLINE_LINES:
                parts.append(f"## Reference: {ref_file.name}\n\n{content}")
            else:
                read_paths.append(str(ref_file))
        except OSError:
            continue

    if not parts and not read_paths:
        return

    ctx_parts = []
    if read_paths:
        paths_list = ", ".join(f"`{p}`" for p in read_paths)
        ctx_parts.append(
            f"[skill-references] REQUIRED: Read these reference files before proceeding: {paths_list}"
        )
    if parts:
        ctx_parts.append("[skill-references] Loaded inline:\n\n" + "\n\n---\n\n".join(parts))

    emit_hook_output(
        "PostToolUse",
        additional_context="\n\n".join(ctx_parts),
    )


if __name__ == "__main__":
    main()
