"""Unit tests for track-workflow-skill.py workflow-state write logic.

Covers the sub-workflow dispatch contract described in the plugin CLAUDE.md
(active-workflow state management section). Focus:

- Fresh start when no prior active-workflow exists.
- Nested dispatch increments invocation_depth and sets caller.
- Same-workflow re-entry is a no-op (preserves started/invocation_depth).
- Stale prior state (> 2h) is treated as fresh start, not nested.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

HOOKS_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS_SCRIPTS))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "track_workflow_skill",
        HOOKS_SCRIPTS / "track-workflow-skill.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def protocol_dir(tmp_path: Path) -> Path:
    """Create a synthetic protocol-testing/bgp tree and return it."""
    root = tmp_path / "protocol-testing" / "bgp"
    (root / ".panther-ivy").mkdir(parents=True)
    return root


def _write_active(protocol_dir: Path, payload: dict[str, Any], started: datetime | None = None) -> None:
    if started is not None:
        payload = {**payload, "started": started.isoformat()}
    (protocol_dir / ".panther-ivy" / "active-workflow").write_text(yaml.safe_dump(payload))


def test_fresh_start_when_no_prior_state(protocol_dir: Path):
    mod = _load_module()
    now = "2026-04-20T12:00:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), None, "verify", now)
    assert kind == "fresh"
    assert new_state == {
        "workflow": "verify",
        "phase": "init",
        "invocation_depth": 0,
        "caller": None,
        "started": now,
    }


def test_same_workflow_reentry_is_noop(protocol_dir: Path):
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(minutes=30)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile", "invocation_depth": 0, "caller": None},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "verify", "2026-04-20T13:00:00+00:00")
    assert kind == "reenter"
    assert new_state is None


def test_nested_dispatch_sets_caller_and_increments_depth(protocol_dir: Path):
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(minutes=10)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile", "invocation_depth": 0, "caller": None},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    now = "2026-04-20T13:05:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "build", now)
    assert kind == "nested"
    assert new_state == {
        "workflow": "build",
        "phase": "init",
        "invocation_depth": 1,
        "caller": "verify",
        "started": now,
    }


def test_stale_prior_state_triggers_fresh_start(protocol_dir: Path):
    mod = _load_module()
    # 5 hours ago → past the 2h staleness threshold in is_workflow_stale
    started = datetime.now(timezone.utc) - timedelta(hours=5)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile", "invocation_depth": 0, "caller": None},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    now = "2026-04-20T13:10:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "build", now)
    assert kind == "fresh"
    assert new_state == {
        "workflow": "build",
        "phase": "init",
        "invocation_depth": 0,
        "caller": None,
        "started": now,
    }


def test_double_nesting_increments_from_one_to_two(protocol_dir: Path):
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(minutes=5)
    _write_active(
        protocol_dir,
        {"workflow": "build", "phase": "init", "invocation_depth": 1, "caller": "verify"},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    now = "2026-04-20T13:15:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "review", now)
    assert kind == "nested"
    assert new_state is not None
    assert new_state["invocation_depth"] == 2
    assert new_state["caller"] == "build"
    assert new_state["workflow"] == "review"


def test_write_state_locked_serializes_under_flock(tmp_path: Path):
    mod = _load_module()
    target = tmp_path / "active-workflow"
    payload = {
        "workflow": "verify",
        "phase": "init",
        "invocation_depth": 0,
        "caller": None,
        "started": "2026-04-20T14:00:00+00:00",
    }
    mod._write_state_locked(str(target), payload)
    roundtrip = yaml.safe_load(target.read_text())
    assert roundtrip == payload
