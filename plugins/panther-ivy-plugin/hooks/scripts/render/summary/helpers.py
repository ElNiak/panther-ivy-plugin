"""Helper utilities for the Stop hook session summary.

Imported by :mod:`render.summary.main`. Holds the file-discovery, lint,
claim-counting, tool-metric, and journal-audit helpers so the entry point
in ``main.py`` stays focused on stdin/stdout glue.

The ``sys.path`` bootstrap below makes ``lib.*`` importable when this module
is imported standalone (e.g. from a test that does
``from render.summary.helpers import check_lint``). When imported through
``main.py`` the bootstrap is redundant but harmless.
"""

import collections
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.hook_utils import is_session_active, resolve_session_id, resolve_sessions_dir
from lib.workflow_state import get_journal_entries, get_scaffold_state_safe

CLAIM_PATTERNS = {
    "resolved": re.compile(r"RESOLVED\("),
    "iut_finding": re.compile(r"IUT_FINDING\("),
    "deferred": re.compile(r"DEFERRED\("),
    "guard_added": re.compile(r"GUARD_ADDED\("),
    "n_a": re.compile(r"N/A\("),
    "known_deviation": re.compile(r"KNOWN_DEVIATION\("),
}


def _resolve_session_start_mtime() -> float | None:
    """Return the current session's SessionStart timestamp as a Unix epoch.

    Reads the first ``SessionStart`` event from
    ``<events_dir>/<session_id>/events.jsonl`` and converts its ISO-8601
    ``timestamp`` field. Returns ``None`` when the session id is unknown,
    the events file is missing, or no ``SessionStart`` event has been
    written yet. Callers should treat ``None`` as "do not filter" and
    keep all files (fail-open).
    """
    session_id = resolve_session_id()
    if not session_id or session_id == "unknown":
        return None
    events_dir = resolve_sessions_dir()
    if not events_dir:
        return None
    events_file = os.path.join(events_dir, session_id, "events.jsonl")
    if not os.path.isfile(events_file):
        return None
    try:
        with open(events_file) as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") != "SessionStart":
                    continue
                ts = event.get("timestamp", "")
                if not ts:
                    continue
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                try:
                    return datetime.fromisoformat(ts).timestamp()
                except ValueError:
                    return None
    except OSError:
        return None
    return None


def _is_under_protocol_testing(path: str) -> bool:
    """Return True if path is under a protocol-testing work tree.

    Walks ancestors of the given path looking for a ``.panther-ivy/``
    marker directory. Any ``.ivy`` file outside such a tree (e.g. scratch
    files at the repo root) is excluded from the lint pass.
    """
    p = Path(path).resolve()
    for ancestor in p.parents:
        if (ancestor / ".panther-ivy").is_dir():
            return True
    return False


def find_modified_ivy_files() -> list[str]:
    """Find .ivy files modified, staged, or newly created in this session.

    Modified (vs HEAD) and staged files are returned unconditionally so
    legitimate uncommitted git deltas always surface. Untracked files
    are additionally filtered by mtime against the current session's
    ``SessionStart`` timestamp, so pre-existing scratch files that
    predate the session do not pollute every Stop summary.

    The mtime filter is fail-open: when the session-start timestamp
    cannot be resolved (no events.jsonl, unknown session id, malformed
    timestamp, or stat() error on the file), the untracked file is
    kept rather than silently dropped.

    Only files whose ancestor tree contains a ``.panther-ivy/`` marker
    directory are included. Scratch ``.ivy`` files at the repo root are
    excluded.
    """
    files: set[str] = set()

    for cmd in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--cached", "--name-only"],
    ):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                p = line.strip()
                if p.endswith(".ivy") and _is_under_protocol_testing(p):
                    files.add(p)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    session_start = _resolve_session_start_mtime()
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            path = line.strip()
            if not path.endswith(".ivy"):
                continue
            if not _is_under_protocol_testing(path):
                continue
            if session_start is None:
                files.add(path)
                continue
            try:
                if os.path.getmtime(path) >= session_start:
                    files.add(path)
            except OSError:
                files.add(path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return sorted(files)


def check_lint(content: str) -> list[str]:
    """Check .ivy file content for structural lint issues."""
    issues: list[str] = []
    lines = content.splitlines()
    if not lines or "#lang ivy1.7" not in lines[0]:
        issues.append("missing #lang header")

    stripped = re.sub(r"#.*", "", content)
    stripped = re.sub(r'"[^"]*"', "", stripped)
    opens = stripped.count("{")
    closes = stripped.count("}")
    if opens != closes:
        issues.append(f"unbalanced braces ({opens}/{closes})")

    return issues


def count_claims(content: str) -> dict[str, int]:
    """Count claim discussion markers in file content."""
    counts: dict[str, int] = {k: 0 for k in CLAIM_PATTERNS}
    for name, pattern in CLAIM_PATTERNS.items():
        counts[name] = len(pattern.findall(content))
    return counts


def gather_tool_metrics() -> str:
    """Read observability JSONL and aggregate tool call metrics.

    Prefers the current session's ``events.jsonl`` (resolved via
    :func:`resolve_session_id`) so concurrent Claude Code sessions sharing
    the same observability directory cannot pollute each other's Stop
    summaries. Falls back to the latest-mtime walk only when the session
    id is ``"unknown"`` or its events file does not exist yet.
    """
    events_dir = resolve_sessions_dir()

    if not os.path.isdir(events_dir):
        return ""

    latest = None

    session_id = resolve_session_id()
    if session_id and session_id != "unknown":
        candidate = os.path.join(events_dir, session_id, "events.jsonl")
        if os.path.isfile(candidate):
            latest = candidate

    if latest is None:
        for root, _dirs, filenames in os.walk(events_dir):
            for fname in filenames:
                if fname == "events.jsonl":
                    path = os.path.join(root, fname)
                    if latest is None or os.path.getmtime(path) > os.path.getmtime(latest):
                        latest = path

    if not latest:
        return ""

    tool_counts: collections.Counter = collections.Counter()
    errors = 0
    try:
        with open(latest) as f:
            for line in f:
                try:
                    event = json.loads(line)
                    etype = event.get("event_type", "")
                    if etype == "PostToolUse":
                        tool = event.get("payload", {}).get("tool_name", "unknown")
                        tool_counts[tool] += 1
                    if etype == "PostToolUseFailure":
                        errors += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        return ""

    if not tool_counts:
        return ""

    top = ", ".join(f"{t}={c}" for t, c in tool_counts.most_common(5))
    return f"Tool calls: {sum(tool_counts.values())} ({top}). Errors: {errors}"


def audit_journal(protocol_dir: str, workflow: str | None) -> list[str]:
    """Check for gaps in journal entries during this session.

    Returns:
        List of warning strings (empty if no issues found).
    """
    if not is_session_active():
        return []
    if not workflow:
        return []

    entries = get_journal_entries(protocol_dir, last_n=50)
    if not entries:
        return ["No journal entries for this session. Workflow state tracking may be incomplete."]

    warnings: list[str] = []

    session_starts = [e for e in entries if e.get("type") == "session_start"]
    if not session_starts:
        warnings.append("No session_start event found. SessionStart hook may not have fired.")

    decisions = [e for e in entries if e.get("type") == "decision"]

    if workflow == "scaffold" and not decisions:
        scaffold_state = get_scaffold_state_safe(protocol_dir)
        if scaffold_state and scaffold_state.get("decisions"):
            warnings.append(
                "Build state has decisions but no decision events were journaled this session."
            )

    return warnings
