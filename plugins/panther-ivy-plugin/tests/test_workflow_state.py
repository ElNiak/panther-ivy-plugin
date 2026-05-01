"""Tests for workflow state utilities."""

import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")


@pytest.fixture(autouse=True)
def _patch_sys_path():
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    if "workflow_state" in sys.modules:
        del sys.modules["workflow_state"]


def _import_module():
    if "workflow_state" in sys.modules:
        return importlib.reload(sys.modules["workflow_state"])
    return importlib.import_module("workflow_state")


class TestSetAndGetActiveWorkflow:
    def test_roundtrip(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-verify", "init")
        result = mod.get_active_workflow(str(tmp_path))
        assert result is not None
        assert result["workflow"] == "workflow-verify"
        assert result["phase"] == "init"
        assert "started" in result
        # post-refactor: active-workflow schema is 3 fields only
        assert set(result.keys()) == {"workflow", "phase", "started"}


class TestUpdatePhase:
    def test_only_phase_changes(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-build", "compile")
        original = mod.get_active_workflow(str(tmp_path))

        mod.update_workflow_phase(str(tmp_path), "link")
        updated = mod.get_active_workflow(str(tmp_path))

        assert updated["phase"] == "link"
        assert updated["workflow"] == original["workflow"]
        assert updated["started"] == original["started"]


class TestClearActiveWorkflow:
    def test_clear_removes_file(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-verify", "init")
        assert mod.get_active_workflow(str(tmp_path)) is not None

        mod.clear_active_workflow(str(tmp_path))
        assert mod.get_active_workflow(str(tmp_path)) is None

    def test_clear_nonexistent_is_noop(self, tmp_path):
        mod = _import_module()
        mod.clear_active_workflow(str(tmp_path))


class TestIsWorkflowStale:
    def test_stale_detection(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-verify", "init")

        state_file = tmp_path / ".panther-ivy" / "active-workflow"
        data = yaml.safe_load(state_file.read_text())
        data["started"] = (
            datetime.now(timezone.utc) - timedelta(hours=3)
        ).isoformat()
        state_file.write_text(yaml.safe_dump(data))

        assert mod.is_workflow_stale(str(tmp_path), max_age_hours=2) is True

    def test_fresh_workflow_is_not_stale(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-verify", "init")
        assert mod.is_workflow_stale(str(tmp_path), max_age_hours=2) is False

    def test_no_workflow_is_not_stale(self, tmp_path):
        mod = _import_module()
        assert mod.is_workflow_stale(str(tmp_path)) is False


class TestMissingDirReturnsNone:
    def test_get_returns_none(self, tmp_path):
        mod = _import_module()
        assert mod.get_active_workflow(str(tmp_path / "nonexistent")) is None

    def test_build_state_returns_none(self, tmp_path):
        mod = _import_module()
        assert mod.get_build_state(str(tmp_path / "nonexistent")) is None


class TestBuildStateRoundtrip:
    def test_write_and_read(self, tmp_path):
        mod = _import_module()
        state = {
            "phase": "compile",
            "targets": ["quic_server_test"],
            "completed": ["quic_types"],
        }
        mod.set_build_state(str(tmp_path), state)
        result = mod.get_build_state(str(tmp_path))
        assert result == state


class TestGetBuildStateParseFailure:
    """Tests for get_build_state() raising on parse failure (cluster-12 S8)."""

    def test_missing_file_returns_none(self, tmp_path):
        mod = _import_module()
        assert mod.get_build_state(str(tmp_path)) is None

    def test_valid_file_returns_dict(self, tmp_path):
        mod = _import_module()
        state = {"phase": "compile", "layers": {"quic_types": "complete"}}
        mod.set_build_state(str(tmp_path), state)
        assert mod.get_build_state(str(tmp_path)) == state

    def test_malformed_yaml_raises(self, tmp_path):
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "build-state.yaml").write_text(
            "phase: compile\n" "  : bad-yaml\n" "layers: [unclosed\n"
        )
        with pytest.raises(mod.BuildStateParseError):
            mod.get_build_state(str(tmp_path))

    def test_non_dict_root_raises(self, tmp_path):
        """A parseable-but-non-dict root (e.g., a YAML list) is a parse failure."""
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "build-state.yaml").write_text("- phase: compile\n- layers: []\n")
        with pytest.raises(mod.BuildStateParseError):
            mod.get_build_state(str(tmp_path))


class TestValidateActiveWorkflow:
    """Tests for validate_active_workflow() (cluster-12 S8)."""

    _KNOWN = {"workflow-navigate", "workflow-build", "workflow-verify", "workflow-review", "workflow-triage"}

    def test_missing_file_is_valid(self, tmp_path):
        mod = _import_module()
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert (ok, reason) == (True, None)

    def test_valid_3_field_schema_passes(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-build", "modeling")
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert (ok, reason) == (True, None)

    def test_corrupt_yaml_is_invalid(self, tmp_path):
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text("workflow: build\n  : bad-yaml\n")
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert ok is False
        assert reason is not None
        assert "YAML parse error" in reason

    def test_unknown_workflow_is_invalid(self, tmp_path):
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            "workflow: imaginary\nphase: modeling\nstarted: '2026-04-23T09:00:00+00:00'\n"
        )
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert ok is False
        assert reason is not None
        assert "imaginary" in reason

    def test_empty_phase_is_invalid(self, tmp_path):
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            "workflow: workflow-build\nphase: ''\nstarted: '2026-04-23T09:00:00+00:00'\n"
        )
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert ok is False
        assert reason is not None
        assert "phase" in reason

    def test_bad_iso_timestamp_is_invalid(self, tmp_path):
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            "workflow: workflow-build\nphase: modeling\nstarted: 'yesterday'\n"
        )
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=self._KNOWN)
        assert ok is False
        assert reason is not None
        assert "started" in reason

    def test_empty_known_workflows_skips_name_check(self, tmp_path):
        """If known_workflows resolves empty (e.g., plugin root unavailable),
        the workflow-name check is skipped but structural checks still run."""
        mod = _import_module()
        state_dir = tmp_path / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            "workflow: anything\nphase: modeling\nstarted: '2026-04-23T09:00:00+00:00'\n"
        )
        ok, reason = mod.validate_active_workflow(str(tmp_path), known_workflows=set())
        assert (ok, reason) == (True, None)


class TestFindProtocolDir:
    def test_from_env_var(self, monkeypatch, tmp_path):
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        mod = _import_module()
        assert mod.find_protocol_dir() == str(proto_dir)

    def test_missing_env_and_no_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.find_protocol_dir() is None

    def test_walk_up_from_cwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        mod = _import_module()
        assert mod.find_protocol_dir() == str(proto_dir)

    def test_protocol_narrows_to_subdir(self, monkeypatch, tmp_path):
        proto_dir = tmp_path / "protocol-testing"
        bgp_dir = proto_dir / "bgp"
        bgp_dir.mkdir(parents=True)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        mod = _import_module()
        assert mod.find_protocol_dir("bgp") == str(bgp_dir)

    def test_protocol_missing_subdir_returns_none(self, monkeypatch, tmp_path):
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        mod = _import_module()
        assert mod.find_protocol_dir("nonexistent") is None

    def test_protocol_with_cwd_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        proto_dir = tmp_path / "protocol-testing"
        quic_dir = proto_dir / "quic"
        quic_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.find_protocol_dir("quic") == str(quic_dir)


class TestAppendJournalEvent:
    """Tests for append_journal_event()."""

    def test_creates_journal_file_on_first_append(self, tmp_path):
        mod = _import_module()
        mod.append_journal_event(
            str(tmp_path),
            event_type="session_start",
            payload={"resumed_from": None},
            workflow="workflow-build",
            phase="init",
        )
        journal_path = tmp_path / ".panther-ivy" / "workflow-journal.yaml"
        assert journal_path.exists()
        entries = yaml.safe_load(journal_path.read_text())
        assert len(entries) == 1
        assert entries[0]["type"] == "session_start"
        assert entries[0]["workflow"] == "workflow-build"
        assert entries[0]["phase"] == "init"
        assert entries[0]["payload"] == {"resumed_from": None}
        assert "ts" in entries[0]

    def test_appends_to_existing_journal(self, tmp_path):
        mod = _import_module()
        mod.append_journal_event(str(tmp_path), "session_start", {"resumed_from": None}, "workflow-build", "init")
        mod.append_journal_event(str(tmp_path), "decision", {"summary": "defer group D", "context": "needs 3-speaker"}, "scaffold", "scoped")

        journal_path = tmp_path / ".panther-ivy" / "workflow-journal.yaml"
        entries = yaml.safe_load(journal_path.read_text())
        assert len(entries) == 2
        assert entries[1]["type"] == "decision"
        assert entries[1]["payload"]["summary"] == "defer group D"

    def test_rejects_invalid_event_type(self, tmp_path):
        mod = _import_module()
        result = mod.append_journal_event(str(tmp_path), "invalid_type", {}, "workflow-build", "init")
        assert result is False

    def test_allows_append_without_active_workflow(self, tmp_path):
        mod = _import_module()
        result = mod.append_journal_event(str(tmp_path), "session_start", {"resumed_from": None}, None, None)
        assert result is True
        journal_path = tmp_path / ".panther-ivy" / "workflow-journal.yaml"
        entries = yaml.safe_load(journal_path.read_text())
        assert entries[0]["workflow"] is None


class TestGetJournalEntries:
    """Tests for get_journal_entries()."""

    def test_returns_empty_list_when_no_journal(self, tmp_path):
        mod = _import_module()
        entries = mod.get_journal_entries(str(tmp_path))
        assert entries == []

    def test_returns_last_n_entries(self, tmp_path):
        mod = _import_module()
        for i in range(10):
            mod.append_journal_event(str(tmp_path), "progress", {"detail": f"step {i}"}, "workflow-build", "init")

        entries = mod.get_journal_entries(str(tmp_path), last_n=3)
        assert len(entries) == 3
        assert entries[0]["payload"]["detail"] == "step 7"
        assert entries[2]["payload"]["detail"] == "step 9"

    def test_returns_all_when_fewer_than_last_n(self, tmp_path):
        mod = _import_module()
        mod.append_journal_event(str(tmp_path), "session_start", {"resumed_from": None}, "workflow-build", "init")
        entries = mod.get_journal_entries(str(tmp_path), last_n=20)
        assert len(entries) == 1


class TestAppendPendingDispatch:
    """Tests for append_pending_dispatch() helper (cluster-1 workflow composition)."""

    def test_appends_minimal_payload(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-build", "phase-4")
        result = mod.append_pending_dispatch(str(tmp_path), "workflow-verify")
        assert result is True

        entries = mod.get_journal_entries(str(tmp_path))
        assert len(entries) == 1
        entry = entries[0]
        assert entry["type"] == "pending_dispatch"
        assert entry["workflow"] == "workflow-build"
        assert entry["phase"] == "phase-4"
        assert entry["payload"] == {"workflow": "workflow-verify"}

    def test_includes_phase_hint_and_reason_when_provided(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-build", "phase-4")
        mod.append_pending_dispatch(
            str(tmp_path),
            "workflow-verify",
            phase_hint="preflight",
            reason="scaffold phase 4 requires verification",
        )
        entry = mod.get_journal_entries(str(tmp_path))[0]
        assert entry["payload"] == {
            "workflow": "workflow-verify",
            "phase_hint": "preflight",
            "reason": "scaffold phase 4 requires verification",
        }

    def test_omits_phase_hint_and_reason_when_none(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "workflow-review", "phase-3")
        mod.append_pending_dispatch(str(tmp_path), "workflow-verify", reason=None)
        entry = mod.get_journal_entries(str(tmp_path))[0]
        assert "phase_hint" not in entry["payload"]
        assert "reason" not in entry["payload"]

    def test_emits_when_no_active_workflow(self, tmp_path):
        """Emitting workflow fields are None when active-workflow is absent."""
        mod = _import_module()
        result = mod.append_pending_dispatch(str(tmp_path), "workflow-triage")
        assert result is True
        entry = mod.get_journal_entries(str(tmp_path))[0]
        assert entry["workflow"] is None
        assert entry["phase"] is None
        assert entry["payload"] == {"workflow": "workflow-triage"}


class TestRotateJournal:
    """Tests for rotate_journal()."""

    def test_rotates_when_exceeding_max_entries(self, tmp_path):
        mod = _import_module()
        for i in range(210):
            mod.append_journal_event(str(tmp_path), "progress", {"detail": f"step {i}"}, "workflow-build", "init")

        mod.rotate_journal(str(tmp_path), max_entries=200)

        entries = mod.get_journal_entries(str(tmp_path), last_n=999)
        assert len(entries) == 105  # kept the newest half (210 // 2 = 105)

        archive_dir = tmp_path / ".panther-ivy" / "journal-archive"
        assert archive_dir.is_dir()
        archive_files = list(archive_dir.iterdir())
        assert len(archive_files) == 1

    def test_no_rotation_when_under_max(self, tmp_path):
        mod = _import_module()
        for i in range(50):
            mod.append_journal_event(str(tmp_path), "progress", {"detail": f"step {i}"}, "workflow-build", "init")

        mod.rotate_journal(str(tmp_path), max_entries=200)

        archive_dir = tmp_path / ".panther-ivy" / "journal-archive"
        assert not archive_dir.exists()
