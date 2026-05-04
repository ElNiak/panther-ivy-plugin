#!/usr/bin/env python3
"""PostToolUse hook on the ``Skill`` matcher: track every skill invocation.

Re-introduces the behavior of the previously-removed ``track-workflow-skill.py``
+ ``auto-load-skill-references.py`` in a single, leaner script. For every
``Skill`` tool call:

  * Emits a ``[ivy-skill] <name> ...`` system message so the user sees the
    skill ran (strict-literal scope).
  * Updates the statusline cache ``active_skill`` section.
  * For plugin skills (``panther-ivy-plugin:*``), auto-loads the skill's
    ``references/`` directory contents into ``additionalContext`` so the
    model receives them without an extra Read. The payload is capped at
    8000 chars to stay well under the 10 000-char ``additionalContext``
    runtime budget; on overflow, the envelope lists file names instead of
    contents and lets the model decide which to Read.

    Load order is alphabetical (``sorted(refs_dir.glob("*.md"))``). The
    first ``_REFERENCES_MAX_FILES`` files are concatenated until the
    cumulative byte count would exceed ``_REFERENCES_BUDGET``; any
    remaining files become a name-only listing in the same envelope. On
    overflow, a ``[references-cap-hit]`` debug line is emitted to stderr
    so contributors investigating reference rot can see which skill hit
    the cap and how many files were inlined vs listed.
  * For ops-skills (``scaffold-ops``, ``refine-ops``, ``experiment-ops``,
    ``review-ops``, ``triage-ops``, ``meta-self-mod-ops``) inside an active workflow,
    appends a ``progress{kind: "skill_invoked"}`` journal entry. The
    orchestrator reads this on its next turn for the warm-resume decision.
  * Non-plugin skills get only the status line — no journal write, no
    reference load.

The hook never blocks. ``hooks.json`` registers it on PostToolUse with
``matcher: "Skill"``; the runtime filters non-Skill events before this
script runs.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.hook_utils import emit_hook_output, emit_noop, mark_session_activity, read_stdin  # noqa: E402
from lib.statusline_cache import update_from_hook as _statusline_update  # noqa: E402
from lib.workflow_state import (  # noqa: E402
    OPS_SKILLS,
    WorkflowContext,
    append_journal_event,
    journal_path,
)

_PLUGIN_PREFIX = "panther-ivy-plugin:"

# Per the plan: stay well below the 10 000-char additionalContext cap so the
# combined envelope (system message + nested fields + JSON braces) doesn't
# get truncated.
_REFERENCES_BUDGET = 8000
_REFERENCES_MAX_FILES = 5


def _resolve_skill_name(tool_input: dict) -> str:
    """Read the skill name from the canonical ``tool_input.skill`` slot."""
    name = tool_input.get("skill", "")
    if not isinstance(name, str):
        return ""
    return name.strip()


def _short_name(skill: str) -> str:
    """Strip the ``panther-ivy-plugin:`` prefix from a plugin skill name."""
    if skill.startswith(_PLUGIN_PREFIX):
        return skill[len(_PLUGIN_PREFIX):]
    return skill


def _references_dir(skill: str) -> Path | None:
    """Return the on-disk ``references/`` directory for a plugin skill, if any."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        return None
    candidate = Path(plugin_root) / "skills" / _short_name(skill) / "references"
    return candidate if candidate.is_dir() else None


def _load_references(refs_dir: Path) -> tuple[str, int, bool]:
    """Concatenate up to N reference files, capped at the budget.

    Files load in alphabetical order (``sorted(refs_dir.glob("*.md"))``).
    Iteration stops when either the file count reaches
    ``_REFERENCES_MAX_FILES`` or the cumulative byte count would exceed
    ``_REFERENCES_BUDGET``. On overflow, the caller switches to a
    name-only listing envelope and a ``[references-cap-hit]`` line is
    emitted to stderr (see caller).

    Returns ``(payload, files_loaded, overflowed)``. ``overflowed`` is True
    when the directory had more than the per-file or per-byte limit and the
    caller should switch to the listing form.
    """
    md_files = sorted(refs_dir.glob("*.md"))
    if not md_files:
        return "", 0, False

    overflowed = len(md_files) > _REFERENCES_MAX_FILES
    chunks: list[str] = []
    total = 0
    files_loaded = 0
    for path in md_files[:_REFERENCES_MAX_FILES]:
        try:
            body = path.read_text()
        except OSError:
            continue
        chunk = f"## references/{path.name}\n\n{body}\n"
        if total + len(chunk) > _REFERENCES_BUDGET:
            overflowed = True
            break
        chunks.append(chunk)
        total += len(chunk)
        files_loaded += 1

    if overflowed:
        listing = "\n".join(f"- references/{p.name}" for p in md_files)
        listing_payload = (
            f"[ivy-skill] references/ directory has "
            f"{len(md_files)} files (over the {_REFERENCES_BUDGET}-char "
            "auto-load budget). Files available:\n"
            f"{listing}\n"
            "Read the ones you need."
        )
        return listing_payload, len(md_files), True

    return "".join(chunks), files_loaded, False


def _log_cap_hit(skill: str, refs_dir: Path, files_loaded: int) -> None:
    """Emit a stderr debug line when the references auto-load cap is hit.

    Stderr is captured by the harness's hook log; the line lets a
    contributor investigating reference rot see which skill hit the cap
    and how many files were inlined vs listed-only. The line is plain
    text (no additionalContext), so it does not consume model context.
    """
    md_files = sorted(refs_dir.glob("*.md"))
    msg = (
        f"[references-cap-hit] skill={_short_name(skill)}"
        f" files_total={len(md_files)} files_inlined={files_loaded}"
        f" budget={_REFERENCES_BUDGET}"
    )
    print(msg, file=sys.stderr)


def _journal_skill_invocation(skill: str, ctx: WorkflowContext) -> None:
    """Append a ``progress{kind: "skill_invoked"}`` event when ops-skill fires."""
    short = _short_name(skill)
    if short not in OPS_SKILLS:
        return
    append_journal_event(
        ctx.protocol_dir,
        event_type="progress",
        payload={
            "kind": "skill_invoked",
            "skill": skill,
            "workflow": ctx.workflow,
            "phase": ctx.phase,
        },
        workflow=ctx.workflow,
        phase=ctx.phase,
    )


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")
    if tool_name != "Skill":
        emit_noop("PostToolUse", f"non-Skill tool ({tool_name or 'unknown'})")
        return

    tool_input = data.get("tool_input", {}) or {}
    if not isinstance(tool_input, dict):
        emit_noop("PostToolUse", "Skill tool_input is not an object")
        return

    skill = _resolve_skill_name(tool_input)
    if not skill:
        emit_noop("PostToolUse", "Skill invocation has no skill name")
        return

    if not skill.startswith(_PLUGIN_PREFIX):
        # Non-plugin skill: surface visibility only; no journal write,
        # no reference auto-load.
        emit_hook_output(
            "PostToolUse",
            system_message=f"[ivy-skill] non-plugin skill: {skill}",
        )
        return

    mark_session_activity(f"skill:{skill}")

    # Plugin skill: update statusline, optionally load references, optionally
    # journal-record the invocation.
    _statusline_update(
        "active_skill",
        {
            "name": skill,
            "invoked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )

    ctx = WorkflowContext.current()
    if ctx is not None:
        _journal_skill_invocation(skill, ctx)
    journal_suffix = (
        f"; skill_invoked appended to journal at {journal_path(ctx.protocol_dir)}"
        if ctx is not None else ""
    )

    refs_dir = _references_dir(skill)
    if refs_dir is None:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-skill] {_short_name(skill)} loaded (no references/)"
                f"{journal_suffix}"
            ),
        )
        return

    payload, files_loaded, overflowed = _load_references(refs_dir)
    if not payload:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-skill] {_short_name(skill)} loaded (empty references/)"
                f"{journal_suffix}"
            ),
        )
        return

    if overflowed:
        _log_cap_hit(skill, refs_dir, files_loaded)

    overflow_tag = " — listing only" if overflowed else ""
    emit_hook_output(
        "PostToolUse",
        system_message=(
            f"[ivy-skill] {_short_name(skill)} loaded "
            f"({files_loaded} ref{'s' if files_loaded != 1 else ''}, "
            f"{len(payload)}B{overflow_tag}){journal_suffix}"
        ),
        additional_context=payload,
    )


if __name__ == "__main__":
    main()
