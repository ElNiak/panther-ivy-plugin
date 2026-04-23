"""Unit tests for hook_utils.read_mcp_health_state / write_mcp_health_state.

These helpers own the MCP circuit-breaker persistence: every PreToolUse
on an ivy tool reads the current failure count via read_mcp_health_state,
and every definitive MCP failure writes back via write_mcp_health_state.
If read returns a stale count or write silently loses data, the circuit
breaker either blocks legitimate tool calls or lets a crashed MCP server
keep being called. These tests pin the round-trip contract, the TTL
auto-reset, and the missing-file defaults.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

import pytest

HOOKS_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS_SCRIPTS))


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "hook_utils", HOOKS_SCRIPTS / "hook_utils.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load hook_utils with the state path scoped to a tmp workspace."""
    monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("IVY_SESSION_ID", "test-session")
    return _load_module()


def _state_path(mod: Any) -> Path:
    return Path(mod.get_mcp_health_state_path())


def test_read_returns_defaults_when_state_file_missing(mod: Any) -> None:
    assert not _state_path(mod).exists()
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 0
    assert state["last_update"] == pytest.approx(time.time(), abs=5)


def test_write_then_read_round_trip(mod: Any) -> None:
    mod.write_mcp_health_state({"consecutive_failures": 2})
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 2
    assert state["last_update"] == pytest.approx(time.time(), abs=5)


def test_write_always_stamps_last_update(mod: Any) -> None:
    mod.write_mcp_health_state(
        {"consecutive_failures": 1, "last_update": 0.0}
    )
    path = _state_path(mod)
    persisted = json.loads(path.read_text())
    assert persisted["last_update"] > 0
    assert persisted["last_update"] == pytest.approx(time.time(), abs=5)


def test_read_returns_defaults_when_state_is_older_than_ttl(
    mod: Any,
) -> None:
    path = _state_path(mod)
    path.parent.mkdir(parents=True, exist_ok=True)
    stale = {
        "consecutive_failures": 9,
        "last_update": time.time() - (mod._MCP_HEALTH_STATE_TTL + 60),
    }
    path.write_text(json.dumps(stale))
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 0
    assert state["last_update"] == pytest.approx(time.time(), abs=5)


def test_read_preserves_state_within_ttl(mod: Any) -> None:
    path = _state_path(mod)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = {
        "consecutive_failures": 2,
        "last_update": time.time() - 10,
    }
    path.write_text(json.dumps(fresh))
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 2
    assert state["last_update"] == pytest.approx(fresh["last_update"], abs=0.1)


def test_sequential_writes_produce_consistent_final_state(mod: Any) -> None:
    mod.write_mcp_health_state({"consecutive_failures": 1})
    mod.write_mcp_health_state({"consecutive_failures": 2})
    mod.write_mcp_health_state({"consecutive_failures": 3})
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 3


def test_read_returns_defaults_on_corrupted_json(mod: Any) -> None:
    path = _state_path(mod)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json")
    state = mod.read_mcp_health_state()
    assert state["consecutive_failures"] == 0


_WORKER_SCRIPT = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, {hooks_scripts!r})
    from hook_utils import read_mcp_health_state, write_mcp_health_state
    for _ in range({iterations}):
        state = read_mcp_health_state()
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        write_mcp_health_state(state)
    """
)


def test_concurrent_writers_never_corrupt_the_state_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke-test fcntl discipline under concurrent writers.

    N worker subprocesses each perform K read-modify-write cycles on the
    same state file. The counter is allowed to exhibit lost updates
    (the helpers lock the read and the write independently, not the
    read-modify-write sequence), but the file must never become
    unparseable and the final counter must be a positive int no larger
    than N*K. If LOCK_EX were silently dropped, a large enough workload
    could produce a partial write that fails json.loads on readback;
    this test catches that regression without relying on timing.
    """
    monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("IVY_SESSION_ID", "concurrent-test")
    mod = _load_module()
    n_workers = 5
    iterations = 20
    env = {**os.environ}
    worker_src = _WORKER_SCRIPT.format(
        hooks_scripts=str(HOOKS_SCRIPTS),
        iterations=iterations,
    )

    procs = [
        subprocess.Popen(
            [sys.executable, "-c", worker_src],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for _ in range(n_workers)
    ]
    for p in procs:
        _, err = p.communicate(timeout=30)
        assert p.returncode == 0, err.decode(errors="replace")

    state = mod.read_mcp_health_state()
    assert isinstance(state["consecutive_failures"], int)
    assert 1 <= state["consecutive_failures"] <= n_workers * iterations
    assert isinstance(state["last_update"], float)
    raw = Path(mod.get_mcp_health_state_path()).read_text()
    assert json.loads(raw) == state
