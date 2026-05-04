"""Tests for the PostToolUse:AskUserQuestion hook ``record/askuserquestion.py``.

The hook records every ``AskUserQuestion`` invocation to a JSONL log under
``.panther-ivy/askuserquestion-log.jsonl`` (always) and additionally appends
a compact ``progress{kind: "question_answered"}`` event to the workflow
journal when an active workflow context is found.

These tests subprocess-invoke the hook so they exercise the end-to-end
JSON-on-stdin → JSON-on-stdout contract, not just the helper internals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "record/askuserquestion.py"

sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))
from lib.workflow_state import set_active_workflow  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Non-AskUserQuestion tool → noop
# ---------------------------------------------------------------------------


class TestNonAskUserQuestionTool:
    def test_non_matching_tool_emits_noop(self, run_hook):
        out = run_hook(SCRIPT, {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "non-AskUserQuestion" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})

    def test_unexpected_payload_shape_emits_noop(self, run_hook):
        out = run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": "not-a-dict",
                "tool_response": [],
            },
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


# ---------------------------------------------------------------------------
# 2. No active workflow → JSONL only, falls back to workspace root
# ---------------------------------------------------------------------------


class TestNoActiveWorkflow:
    def test_writes_jsonl_under_workspace_root(self, run_hook, tmp_path):
        (tmp_path / "protocol-testing").mkdir()
        env = {"IVY_WORKSPACE_ROOT": str(tmp_path)}
        out = run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": {
                    "questions": [
                        {
                            "question": "Pick a colour?",
                            "header": "Colour",
                            "multiSelect": False,
                            "options": [
                                {"label": "red", "description": "the red one"},
                                {"label": "blue", "description": "the blue one"},
                            ],
                        }
                    ]
                },
                "tool_response": {"answers": {"Pick a colour?": "red"}},
            },
            env=env,
            cwd=tmp_path,
        )

        assert "[ivy-question] recorded 1 question(s), 1 answer(s)" in out["systemMessage"]
        log_file = tmp_path / ".panther-ivy" / "askuserquestion-log.jsonl"
        assert log_file.is_file()
        records = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
        assert len(records) == 1
        record = records[0]
        assert record["active_workflow"] is False
        assert "workflow" not in record
        assert record["answers"] == {"Pick a colour?": "red"}
        assert record["questions"][0]["header"] == "Colour"

    def test_no_workspace_root_skips_jsonl(self, run_hook, tmp_path):
        env = {"IVY_WORKSPACE_ROOT": ""}
        out = run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": {"questions": [{"question": "Q?", "header": "Q", "multiSelect": False, "options": []}]},
                "tool_response": {"answers": {"Q?": "A"}},
            },
            env=env,
            cwd=tmp_path,
        )
        assert "[ivy-question]" in out["systemMessage"]


# ---------------------------------------------------------------------------
# 3. Active workflow → JSONL under protocol-dir + journal entry
# ---------------------------------------------------------------------------


class TestActiveWorkflow:
    @pytest.fixture
    def active_protocol(self, tmp_path: Path) -> Path:
        protocol_dir = tmp_path / "protocol-testing" / "test_proto"
        protocol_dir.mkdir(parents=True)
        set_active_workflow(str(protocol_dir), "scaffold", "Phase 3")
        return protocol_dir

    def test_writes_jsonl_to_protocol_dir(self, run_hook, tmp_path, active_protocol):
        env = {"IVY_WORKSPACE_ROOT": str(tmp_path)}
        out = run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": {
                    "questions": [
                        {
                            "question": "Multi?",
                            "header": "Pick",
                            "multiSelect": True,
                            "options": [
                                {"label": "A", "description": "a"},
                                {"label": "B", "description": "b"},
                            ],
                        }
                    ]
                },
                "tool_response": {
                    "answers": {"Multi?": "A, B"},
                    "annotations": {"Multi?": {"notes": "user typed extra context"}},
                },
            },
            env=env,
            cwd=tmp_path,
        )
        assert "[ivy-question] recorded 1 question(s), 1 answer(s)" in out["systemMessage"]

        log_file = active_protocol / ".panther-ivy" / "askuserquestion-log.jsonl"
        assert log_file.is_file()
        records = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
        assert len(records) == 1
        record = records[0]
        assert record["active_workflow"] is True
        assert record["workflow"] == "scaffold"
        assert record["phase"] == "Phase 3"
        assert record["annotations"] == {"Multi?": {"notes": "user typed extra context"}}

    def test_appends_journal_event(self, run_hook, tmp_path, active_protocol):
        env = {"IVY_WORKSPACE_ROOT": str(tmp_path)}
        run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": {
                    "questions": [
                        {"question": "Q1?", "header": "1", "multiSelect": False, "options": []},
                        {"question": "Q2?", "header": "2", "multiSelect": False, "options": []},
                    ]
                },
                "tool_response": {"answers": {"Q1?": "yes", "Q2?": "no"}},
            },
            env=env,
            cwd=tmp_path,
        )

        journal_path = active_protocol / ".panther-ivy" / "workflow-journal.yaml"
        assert journal_path.is_file()
        entries = yaml.safe_load(journal_path.read_text()) or []
        question_events = [
            e for e in entries
            if e.get("type") == "progress"
            and isinstance(e.get("payload"), dict)
            and e["payload"].get("kind") == "question_answered"
        ]
        assert len(question_events) == 1
        payload = question_events[0]["payload"]
        assert payload["question_count"] == 2
        assert payload["answer_count"] == 2
        assert "record_id" in payload

    def test_appends_to_existing_jsonl(self, run_hook, tmp_path, active_protocol):
        log_file = active_protocol / ".panther-ivy" / "askuserquestion-log.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text('{"id": "preexisting", "ts": "2026-01-01T00:00:00+00:00"}\n')
        env = {"IVY_WORKSPACE_ROOT": str(tmp_path)}
        run_hook(
            SCRIPT,
            {
                "tool_name": "AskUserQuestion",
                "tool_input": {
                    "questions": [{"question": "Q?", "header": "Q", "multiSelect": False, "options": []}]
                },
                "tool_response": {"answers": {"Q?": "A"}},
            },
            env=env,
            cwd=tmp_path,
        )
        records = [json.loads(line) for line in log_file.read_text().splitlines() if line.strip()]
        assert len(records) == 2
        assert records[0]["id"] == "preexisting"
        assert records[1]["active_workflow"] is True
