"""Tests for scripts/migrate-bootstrap-project-md.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "scripts" / "migrate-bootstrap-project-md.py"


def _read_state(project_md: Path) -> dict:
    text = project_md.read_text()
    fence = text.split("---\n", 2)
    return yaml.safe_load(fence[1])


def test_bootstraps_each_protocol_with_idle_default(tmp_path):
    for protocol in ("bgp", "quic", "apt", "minip", "coap"):
        (tmp_path / "protocol-testing" / protocol).mkdir(parents=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    for protocol in ("bgp", "quic", "apt", "minip", "coap"):
        target = tmp_path / "protocol-testing" / protocol / "PROJECT.md"
        assert target.exists(), f"missing {target}"
        state = _read_state(target)
        assert state["protocol"] == protocol
        assert state["mode"] == "idle"
        assert state["phase"] == 0
        assert state["last_verify"]["status"] == "NOT_RUN"


def test_skips_existing_project_md(tmp_path):
    bgp = tmp_path / "protocol-testing" / "bgp"
    bgp.mkdir(parents=True)
    pre = bgp / "PROJECT.md"
    pre.write_text("custom-content")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert pre.read_text() == "custom-content"
    assert "skip" in proc.stdout.lower()


def test_skips_protocols_without_existing_dir(tmp_path):
    (tmp_path / "protocol-testing" / "bgp").mkdir(parents=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert (tmp_path / "protocol-testing" / "bgp" / "PROJECT.md").exists()
    for absent in ("quic", "apt", "minip", "coap"):
        assert not (tmp_path / "protocol-testing" / absent / "PROJECT.md").exists()


def test_summary_line_emitted(tmp_path):
    (tmp_path / "protocol-testing" / "bgp").mkdir(parents=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "summary:" in proc.stdout
    assert "1 bootstrapped" in proc.stdout
