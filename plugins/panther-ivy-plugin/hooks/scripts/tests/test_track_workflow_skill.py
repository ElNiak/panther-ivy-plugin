"""Unit tests for track-workflow-skill.py workflow-state write logic.

Covers the simplified 3-field active-workflow schema from the cluster-1
workflow state-model refactor. Focus:

- Fresh start when no prior active-workflow exists (writes new 3-field dict).
- Same-workflow re-entry is a no-op (preserves ``started``).
- Different workflow => overwrite with a fresh timestamp. There is no caller
  chain, no ``invocation_depth``, and no staleness branch — workflow
  composition is journaled via ``pending_dispatch`` events instead.
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
    assert kind == "overwrite"
    assert new_state == {
        "workflow": "verify",
        "phase": "init",
        "started": now,
    }


def test_same_workflow_reentry_is_noop(protocol_dir: Path):
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(minutes=30)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile"},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "verify", "2026-04-20T13:00:00+00:00")
    assert kind == "reenter"
    assert new_state is None


def test_different_workflow_overwrites_fresh(protocol_dir: Path):
    """Any non-matching prior state is overwritten with a 3-field dict."""
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(minutes=10)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile"},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    now = "2026-04-20T13:05:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "build", now)
    assert kind == "overwrite"
    assert new_state == {
        "workflow": "build",
        "phase": "init",
        "started": now,
    }


def test_overwrite_does_not_depend_on_staleness(protocol_dir: Path):
    """The staleness branch was removed in cluster-1; stale prior => overwrite."""
    mod = _load_module()
    started = datetime.now(timezone.utc) - timedelta(hours=5)
    _write_active(
        protocol_dir,
        {"workflow": "verify", "phase": "compile"},
        started=started,
    )
    prev = yaml.safe_load((protocol_dir / ".panther-ivy" / "active-workflow").read_text())
    now = "2026-04-20T13:10:00+00:00"
    new_state, kind = mod._compute_new_state(str(protocol_dir), prev, "build", now)
    assert kind == "overwrite"
    assert new_state == {
        "workflow": "build",
        "phase": "init",
        "started": now,
    }


def test_write_state_locked_serializes_under_flock(tmp_path: Path):
    mod = _load_module()
    target = tmp_path / "active-workflow"
    payload = {
        "workflow": "verify",
        "phase": "init",
        "started": "2026-04-20T14:00:00+00:00",
    }
    mod._write_state_locked(str(target), payload)
    roundtrip = yaml.safe_load(target.read_text())
    assert roundtrip == payload
