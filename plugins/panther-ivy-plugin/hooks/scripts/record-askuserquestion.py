#!/usr/bin/env python3
"""PostToolUse hook on the ``AskUserQuestion`` matcher: log every Q-and-A.

Captures the question text, options, and user answer for each
``AskUserQuestion`` tool call so the user can audit which questions were
asked and how they were answered.

Storage is hybrid:

  * **Always**: append one JSONL record to
    ``<protocol_dir>/.panther-ivy/askuserquestion-log.jsonl`` when an
    active workflow exposes a protocol directory; otherwise to
    ``<workspace_root>/.panther-ivy/askuserquestion-log.jsonl``. If neither
    can be resolved the JSONL append is skipped (the system message still
    surfaces for visibility).
  * **When a workflow is active**: also append a
    ``progress{kind: "question_answered"}`` event to the workflow journal
    via ``append_journal_event``. The journal entry omits the question
    text — only counts and a JSONL-line index — so the YAML stays compact;
    grep the JSONL for the full content.

Subagents do not normally have ``AskUserQuestion`` in their tool allowlist,
so this hook captures essentially every user-facing question without any
subagent-aware special-casing. The hook does check ``tool_name`` exactly
to remain inert for any non-AskUserQuestion invocation.

Always exits 0. The hook is informational; failing the tool call would
discard a user response.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import (  # noqa: E402
    emit_hook_output,
    emit_noop,
    get_workspace_root,
    read_stdin,
    resolve_session_id,
)
from workflow_state import (  # noqa: E402
    STATE_DIR_NAME,
    WorkflowContext,
    append_journal_event,
)

_LOG_FILENAME = "askuserquestion-log.jsonl"


def _resolve_log_dir(ctx: WorkflowContext | None) -> Path | None:
    """Pick the directory that holds the JSONL log.

    Preference order: active-workflow protocol directory (most specific)
    → workspace root (standalone-Ivy-project fallback). Returns ``None``
    when neither is resolvable; the caller skips the JSONL append in that
    case.
    """
    if ctx is not None:
        return Path(ctx.protocol_dir) / STATE_DIR_NAME
    workspace_root = get_workspace_root().strip()
    if not workspace_root:
        return None
    return Path(workspace_root) / STATE_DIR_NAME


def _build_record(
    *,
    hook_input: dict[str, Any],
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
    annotations: dict[str, Any] | None,
    ctx: WorkflowContext | None,
    record_id: str,
) -> dict[str, Any]:
    """Shape a single JSONL record. Order is stable for diff-friendly output."""
    record: dict[str, Any] = {
        "id": record_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": resolve_session_id(hook_input),
        "questions": questions,
        "answers": answers,
        "active_workflow": ctx is not None,
    }
    if ctx is not None:
        record["workflow"] = ctx.workflow
        record["phase"] = ctx.phase
        record["protocol_dir"] = ctx.protocol_dir
    if annotations:
        record["annotations"] = annotations
    return record


def _append_jsonl(log_dir: Path, record: dict[str, Any]) -> Path | None:
    """Append the record to ``<log_dir>/askuserquestion-log.jsonl``.

    Creates ``log_dir`` if it does not exist. Returns the file path on
    success, ``None`` on any I/O failure (the hook never fails the tool
    call, so a write failure is swallowed and reported via the system
    message instead).
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / _LOG_FILENAME
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return log_path
    except OSError:
        return None


def _journal_question_answered(
    *,
    ctx: WorkflowContext,
    record_id: str,
    question_count: int,
    answer_count: int,
) -> None:
    """Append a compact ``progress{kind: question_answered}`` journal event."""
    append_journal_event(
        ctx.protocol_dir,
        event_type="progress",
        payload={
            "kind": "question_answered",
            "record_id": record_id,
            "question_count": question_count,
            "answer_count": answer_count,
        },
        workflow=ctx.workflow,
        phase=ctx.phase,
    )


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")
    if tool_name != "AskUserQuestion":
        emit_noop("PostToolUse", f"non-AskUserQuestion tool ({tool_name or 'unknown'})")
        return

    tool_input = data.get("tool_input", {}) or {}
    tool_response = data.get("tool_response", {}) or {}
    if not isinstance(tool_input, dict) or not isinstance(tool_response, dict):
        emit_noop("PostToolUse", "AskUserQuestion payload shape unexpected")
        return

    questions = tool_input.get("questions") or []
    if not isinstance(questions, list):
        questions = []
    answers = tool_response.get("answers") or {}
    if not isinstance(answers, dict):
        answers = {}
    annotations = tool_response.get("annotations")
    if annotations is not None and not isinstance(annotations, dict):
        annotations = None

    ctx = WorkflowContext.current()
    record_id = uuid.uuid4().hex[:12]
    record = _build_record(
        hook_input=data,
        questions=questions,
        answers=answers,
        annotations=annotations,
        ctx=ctx,
        record_id=record_id,
    )

    log_dir = _resolve_log_dir(ctx)
    log_path = _append_jsonl(log_dir, record) if log_dir is not None else None

    if ctx is not None:
        _journal_question_answered(
            ctx=ctx,
            record_id=record_id,
            question_count=len(questions),
            answer_count=len(answers),
        )

    qcount = len(questions)
    acount = len(answers)
    location = str(log_path) if log_path is not None else "(no log dir)"
    emit_hook_output(
        "PostToolUse",
        system_message=(
            f"[ivy-question] recorded {qcount} question(s), {acount} answer(s) "
            f"to {location} (id={record_id})"
        ),
    )


if __name__ == "__main__":
    main()
