"""Cache path resolution for the panther-ivy-plugin statusline cache.

Computes per-workspace and per-session overlay paths, and provides the
active_group resolver that reads ``.ivy-workspace-state.json``.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

CACHE_VERSION = 1

_DEFAULT_CACHE_ROOT = Path.home() / ".claude" / "panther-ivy-plugin" / "cache"

# Sentinel partition for sessions without an explicit ivy_workspace selection.
# Existing pre-partitioning cache files migrate under this name.
_DEFAULT_GROUP = "default"

# Filesystem-safe path-component regex shared by ``active_group`` and
# ``session_id`` validators. Both fields end up as a single path component
# under the cache directory, so the safety rule (no path traversal, no
# slashes, no empty values) is identical. Active-group examples: bgp,
# quic, apt, apt_quic, minip, coap, scaffolds. Session IDs are UUIDs
# (e.g. "00893aaf-19fa-41d2-8238-13269b9b3ca0") plus broader test-fixture
# names like ``"sess_alpha"``.
_VALID_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _cache_root() -> Path:
    """Resolve the cache root directory, honoring the test override env var.

    Returns:
        Absolute path to the directory holding per-workspace cache folders.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_ROOT", "").strip()
    if override:
        return Path(override)
    return _DEFAULT_CACHE_ROOT


def _workspace_digest(workspace_root: str) -> str:
    """Return the 12-character SHA1 digest used as the per-workspace cache bucket."""
    return hashlib.sha1(workspace_root.encode("utf-8")).hexdigest()[:12]


def _normalize_active_group(active_group: str | None) -> str:
    """Sanitize ``active_group`` for use as a filesystem path component.

    Empty / unsafe values collapse to :data:`_DEFAULT_GROUP`. The
    validation regex blocks path traversal (``..``), absolute paths, and
    non-printable characters that would let a malformed
    ``.ivy-workspace-state.json`` write outside the cache directory.
    """
    if not active_group:
        return _DEFAULT_GROUP
    if not _VALID_PATH_COMPONENT_RE.match(active_group):
        return _DEFAULT_GROUP
    return active_group


def _resolve_active_group(workspace_root: str) -> str:
    """Return the current ``ivy_workspace`` selection or :data:`_DEFAULT_GROUP`.

    Reads ``<workspace_root>/.ivy-workspace-state.json::active_group`` —
    the canonical state file that ``ivy_workspace(action="set", target=...)``
    writes (see ``submodules/ivy-lsp/.../active_workspace.py:save``). Any
    failure (file missing, unreadable, malformed JSON, missing field, null
    field, or the field failing the safety regex) degrades gracefully to
    :data:`_DEFAULT_GROUP` so a session with no explicit selection still
    gets a deterministic partition.

    Args:
        workspace_root: Absolute path to the Ivy workspace root, typically
            the ``panther_ivy/`` directory.

    Returns:
        Either the validated ``active_group`` from the state file, or
        :data:`_DEFAULT_GROUP` when the state file is unavailable or the
        value is unsafe.
    """
    if not workspace_root:
        return _DEFAULT_GROUP
    state_path = Path(workspace_root) / ".ivy-workspace-state.json"
    if not state_path.is_file():
        return _DEFAULT_GROUP
    try:
        with state_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_GROUP
    if not isinstance(data, dict):
        return _DEFAULT_GROUP
    return _normalize_active_group(data.get("active_group"))


def cache_path_for(workspace_root: str, active_group: str | None = None) -> Path:
    """Return the cache file path for a workspace root + active-group bucket.

    Args:
        workspace_root: Absolute path to the Ivy workspace root (typically the
            ``panther_ivy/`` directory or a specific ``protocol-testing/<p>/``).
        active_group: The current ``ivy_workspace`` selection (e.g. ``"bgp"``,
            ``"quic"``). When ``None`` or unsafe, falls back to
            :data:`_DEFAULT_GROUP` so a session that never called
            ``ivy_workspace(set)`` still gets a deterministic cache path.

    Returns:
        Absolute path to the bucket's ``statusline.json`` cache file. The
        ``PANTHER_IVY_STATUSLINE_CACHE_PATH`` env override short-circuits
        all path computation and returns the literal override path; tests
        that pre-date partitioning rely on this behaviour.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_PATH", "").strip()
    if override:
        return Path(override)

    digest = _workspace_digest(workspace_root)
    group = _normalize_active_group(active_group)
    return _cache_root() / digest / group / "statusline.json"


def overlay_path_for(
    workspace_root: str,
    session_id: str,
    active_group: str | None = None,
) -> Path:
    """Return the per-session overlay file path within the active-group bucket.

    The overlay holds session-private statusline state (per-session
    ``test_file``, badge metadata, ``active_skill``) so two Claude Code
    windows in the same workspace+protocol do not overwrite each other's
    transient view. Falls through to :data:`_DEFAULT_GROUP` when
    ``active_group`` is unset, mirroring :func:`cache_path_for`.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        session_id: Stable Claude Code session identifier (a UUID like
            ``"00893aaf-19fa-41d2-8238-13269b9b3ca0"``). The
            ``PANTHER_IVY_STATUSLINE_OVERLAY_PATH`` env override
            short-circuits the computation, mirroring
            :data:`PANTHER_IVY_STATUSLINE_CACHE_PATH` for tests.

    Returns:
        Absolute path to ``<wsHash>/<group>/sessions/<session_id>/overlay.json``,
        or the env override when set.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", "").strip()
    if override:
        return Path(override)

    digest = _workspace_digest(workspace_root)
    group = _normalize_active_group(active_group)
    return (
        _cache_root() / digest / group / "sessions" / session_id / "overlay.json"
    )
