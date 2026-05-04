"""Tests for the SessionStart hook ``statusline/sync.py``.

The hook mirrors the canonical active-workflow YAML into the per-workspace
statusline cache at SessionStart. It is intentionally NOT a legacy-name
normalizer (per ``.claude/rules/journaling-contract.md`` §9 and
``feedback_no_backward_compat_shims``): legacy or unknown YAML values cause
the cache section to be cleared, prompting the user to run the one-shot
``scripts/migrate_legacy_workflow.py``.

Four scenarios:

  1. Canonical YAML with a legacy cache value → cache mirrored to the
     canonical name; ``[ivy-statusline] synced workflow`` system message.
  2. Legacy YAML → cache ``workflow`` section cleared; system message names
     the offending value and points at the migration script.
  3. Missing YAML with a leftover cache value → cache section cleared;
     system message announces the cleanup.
  4. Missing YAML with no cache → ``[ivy-noop]`` (nothing to do).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "statusline/sync.py"


def _setup_workspace(
    tmp_path: Path,
    *,
    workflow_value: str | None = "scaffold",
) -> tuple[Path, Path]:
    """Build a panther_ivy/ workspace with one ``protocol-testing/bgp/`` subtree.

    Args:
        tmp_path: pytest tmp_path fixture root.
        workflow_value: When not None, write
            ``protocol-testing/bgp/.panther-ivy/active-workflow`` with
            ``workflow: <value>``. When None, leave the YAML missing.

    Returns:
        ``(workspace_root, cache_path)``: the panther_ivy/ root the hook
        will resolve from ``IVY_WORKSPACE_ROOT`` and the per-workspace
        ``statusline.json`` path the hook will write via the
        ``PANTHER_IVY_STATUSLINE_CACHE_PATH`` override.
    """
    ws_root = tmp_path / "panther_ivy"
    proto_dir = ws_root / "protocol-testing" / "bgp"
    state_dir = proto_dir / ".panther-ivy"
    state_dir.mkdir(parents=True)
    if workflow_value is not None:
        with (state_dir / "active-workflow").open("w") as fh:
            yaml.safe_dump(
                {
                    "workflow": workflow_value,
                    "phase": "init",
                    "started": "2026-05-02T12:00:00+00:00",
                },
                fh,
            )
    cache_path = tmp_path / "cache_root" / "ws" / "statusline.json"
    cache_path.parent.mkdir(parents=True)
    return ws_root, cache_path


def _write_cache(cache_path: Path, workflow_section: dict | None) -> None:
    """Pre-seed ``cache_path`` with an optional ``workflow`` section."""
    payload: dict = {"version": 1}
    if workflow_section is not None:
        payload["workflow"] = workflow_section
    cache_path.write_text(json.dumps(payload))


def _read_cache(cache_path: Path) -> dict:
    """Read the statusline cache JSON; missing file returns an empty dict."""
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text())


@pytest.fixture
def env_for():
    """Build the env dict the hook needs to find workspace + cache root."""

    def _make(ws_root: Path, cache_path: Path) -> dict:
        return {
            "IVY_WORKSPACE_ROOT": str(ws_root),
            "PANTHER_IVY_STATUSLINE_CACHE_PATH": str(cache_path),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
        }

    return _make


class TestMirrorCanonical:
    def test_canonical_yaml_overwrites_legacy_cache(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value="scaffold")
        _write_cache(cache_path, {"name": "workflow-triage", "phase": "init"})
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert cached["workflow"]["name"] == "scaffold"
        assert cached["workflow"]["phase"] == "init"
        # T3 template per output-style.md: "[ivy-<surface>] <thing>: <new> (was: <prev>)"
        assert (
            "[ivy-statusline] workflow: scaffold (was: workflow-triage)"
            in out["systemMessage"]
        )


class TestLegacyName:
    def test_legacy_yaml_clears_cache_section(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(
            tmp_path, workflow_value="workflow-triage"
        )
        _write_cache(cache_path, {"name": "workflow-triage", "phase": "init"})
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert "workflow" not in cached, (
            "cache workflow section should be cleared when YAML holds a legacy "
            "name; sync hook must not silently normalize"
        )
        assert "non-canonical workflow 'workflow-triage'" in out["systemMessage"]
        assert (
            "migrate_legacy_workflow.py"
            in out["hookSpecificOutput"]["additionalContext"]
        )


class TestNoActiveYaml:
    def test_missing_yaml_clears_stale_cache(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value=None)
        _write_cache(cache_path, {"name": "scaffold", "phase": "init"})
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert "workflow" not in cached
        assert "[ivy-statusline]" in out["systemMessage"]
        assert "cleared" in out["systemMessage"]
        assert "scaffold" in out["systemMessage"]

    def test_missing_yaml_and_no_cache_emits_noop(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value=None)
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        assert out["systemMessage"].startswith("[ivy-noop]")
        assert "no active-workflow YAML and no cache" in out["systemMessage"]


class TestNoOpWhenCacheMatches:
    """Cache value already equals canonical payload -> emit_noop, no rewrite
    (efficiency: avoid fsync per fire on hot path).
    """

    def test_cache_already_matches_yaml_emits_noop(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value="scaffold")
        # Pre-seed cache with the EXACT canonical payload the hook would write.
        _write_cache(
            cache_path,
            {
                "name": "scaffold",
                "phase": "init",
                "invocation_depth": 0,
                "caller": None,
                "started": "2026-05-02T12:00:00+00:00",
            },
        )
        before_mtime = cache_path.stat().st_mtime_ns
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        after_mtime = cache_path.stat().st_mtime_ns
        assert out["systemMessage"].startswith("[ivy-noop]")
        assert "already mirrors active-workflow (scaffold)" in out["systemMessage"]
        # Strongest check: the cache file was NOT rewritten.
        assert before_mtime == after_mtime, (
            "cache file mtime changed despite no-op match; update_section "
            "should be skipped when payload equals existing cache_workflow"
        )


class TestSeedFreshCache:
    """Canonical YAML, no prior cache section -> seed (review-spawned coverage
    for the formerly-uncovered first-time-session branch).
    """

    def test_canonical_yaml_no_prior_cache_seeds(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value="scaffold")
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert cached["workflow"]["name"] == "scaffold"
        # T3 with sentinel <none> for the prior value.
        assert "workflow: scaffold (was: <none>)" in out["systemMessage"]
        assert "seeded" in out["systemMessage"]


class TestLegacyNameNoPriorCache:
    """Legacy YAML + no prior cache: nothing to clear; message must not claim
    a clear happened (Important #2 from code review).
    """

    def test_legacy_yaml_no_prior_cache_does_not_claim_clear(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(
            tmp_path, workflow_value="workflow-triage"
        )
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert "workflow" not in cached
        assert "non-canonical workflow 'workflow-triage'" in out["systemMessage"]
        assert "no cache section to clear" in out["systemMessage"]
        # Must NOT claim a clear happened when none did.
        assert "cleared cache section" not in out["systemMessage"]


class TestMalformedInputs:
    """Edge cases around malformed YAML / cache shapes (Minor #4 coverage)."""

    def test_empty_workflow_string_emits_noop(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value="")
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        assert out["systemMessage"].startswith("[ivy-noop]")
        assert "missing 'workflow' field" in out["systemMessage"]

    def test_cache_workflow_not_a_dict_treated_as_missing(
        self, run_hook, tmp_path: Path, env_for
    ):
        ws_root, cache_path = _setup_workspace(tmp_path, workflow_value="scaffold")
        # Pre-seed cache with a non-dict workflow value (shape corruption).
        cache_path.write_text(json.dumps({"version": 1, "workflow": "scaffold"}))
        out = run_hook(SCRIPT, payload={}, env=env_for(ws_root, cache_path))
        cached = _read_cache(cache_path)
        assert cached["workflow"]["name"] == "scaffold"  # rewritten as proper dict
        # Treated as "no prior cache_workflow" -> seed branch fires.
        assert "seeded" in out["systemMessage"]

    def test_missing_workspace_emits_noop(
        self, run_hook, tmp_path: Path, env_for
    ):
        # IVY_WORKSPACE_ROOT pointing at a dir without protocol-testing/.
        # Pass cwd=ws_root explicitly so the cwd walk-up fallback in
        # _resolve_workspace_root cannot land on the real worktree.
        ws_root = tmp_path / "empty"
        ws_root.mkdir()
        cache_path = tmp_path / "cache_root" / "ws" / "statusline.json"
        cache_path.parent.mkdir(parents=True)
        env = {
            "IVY_WORKSPACE_ROOT": str(ws_root),
            "PANTHER_IVY_STATUSLINE_CACHE_PATH": str(cache_path),
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
        }
        out = run_hook(SCRIPT, payload={}, env=env, cwd=ws_root)
        assert out["systemMessage"].startswith("[ivy-noop]")
        # Either workspace or protocol-dir branch — both legitimate outcomes.
        assert (
            "no panther_ivy workspace detected" in out["systemMessage"]
            or "no protocol directory detected" in out["systemMessage"]
        )
