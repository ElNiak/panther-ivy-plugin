#!/usr/bin/env python3
"""Stop hook: workflow-aware session summary.

Replaces stop-session-summary.sh. Absorbs all existing functionality (lint
scan, claim counts, tool metrics) and routes through workflow-specific
summary templates.

Non-blocking -- always exits 0.
"""

import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin, resolve_sessions_dir
from workflow_state import WorkflowContext, get_build_state, get_journal_entries

CLAIM_PATTERNS = {
    "resolved": re.compile(r"RESOLVED\("),
    "iut_finding": re.compile(r"IUT_FINDING\("),
    "deferred": re.compile(r"DEFERRED\("),
    "guard_added": re.compile(r"GUARD_ADDED\("),
    "n_a": re.compile(r"N/A\("),
    "known_deviation": re.compile(r"KNOWN_DEVIATION\("),
}


def find_modified_ivy_files() -> list[str]:
    """Find .ivy files modified in the working tree."""
    files: set[str] = set()
    for cmd in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if line.strip().endswith(".ivy"):
                    files.add(line.strip())
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
    """Read observability JSONL and aggregate tool call metrics."""
    events_dir = resolve_sessions_dir()

    if not os.path.isdir(events_dir):
        return ""

    latest = None
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

    if workflow == "build" and not decisions:
        build_state = get_build_state(protocol_dir)
        if build_state and build_state.get("decisions"):
            warnings.append(
                "Build state has decisions but no decision events were journaled this session."
            )

    return warnings


def build_summary(
    ivy_files: list[str],
    workflow: str | None,
    phase: str | None,
    protocol_dir: str | None,
) -> str:
    """Build the session summary string."""
    file_count = len(ivy_files)

    # Read each file once for lint and claim analysis
    lint_issues: list[str] = []
    total_claims: dict[str, int] = {k: 0 for k in CLAIM_PATTERNS}
    for f in ivy_files:
        try:
            content = Path(f).read_text()
        except OSError:
            continue
        issues = check_lint(content)
        if issues:
            lint_issues.append(f"  - {f}: {', '.join(issues)}")
        for k, v in count_claims(content).items():
            total_claims[k] += v
    claim_total = sum(total_claims.values())

    # Tool metrics
    metrics = gather_tool_metrics()

    # Build state (for build workflow)
    build_state = None
    if workflow == "build" and protocol_dir:
        build_state = get_build_state(protocol_dir)

    # Compose summary
    parts: list[str] = []

    # Header
    if lint_issues:
        parts.append(
            f"[IVY SESSION SUMMARY] {file_count} .ivy file(s) modified, "
            f"{len(lint_issues)} with lint issues:\n" + "\n".join(lint_issues) + "\n"
            "Run ivy_diagnostics(mode=\"structural\") on flagged files before committing."
        )
    else:
        parts.append(
            f"[IVY SESSION SUMMARY] {file_count} .ivy file(s) modified, "
            "all pass basic structural checks."
        )

    # Workflow-specific section
    if workflow == "verify":
        if phase:
            parts.append(f"[WORKFLOW] Verify workflow ended in phase: {phase}")

    elif workflow == "build" and build_state:
        layers = build_state.get("layers", {})
        if layers:
            layer_lines = ["[BUILD PROGRESS]"]
            for name, info in layers.items():
                status = info.get("status", "pending") if isinstance(info, dict) else info
                layer_lines.append(f"  - {name}: {status}")
            parts.append("\n".join(layer_lines))

    elif workflow == "triage":
        if phase:
            parts.append(f"[TRIAGE] Ended in phase: {phase}")

    elif workflow == "review":
        parts.append("[REVIEW] Review workflow session.")

    elif workflow == "navigate":
        parts.append("[WORKFLOW] Navigate workflow session.")

    # Claims section
    if claim_total > 0:
        claim_parts = [f"[CLAIM DISCUSSIONS] {claim_total} resolution(s):"]
        for label, key in [
            ("confirmed", "resolved"),
            ("IUT findings", "iut_finding"),
            ("guards added", "guard_added"),
            ("deferred", "deferred"),
            ("N/A", "n_a"),
            ("known deviations", "known_deviation"),
        ]:
            if total_claims[key] > 0:
                claim_parts.append(f" {total_claims[key]} {label},")
        claim_line = "".join(claim_parts).rstrip(",")
        parts.append(claim_line)

    # Metrics
    if metrics:
        parts.append(f"[TOOL METRICS] {metrics}")

    # Journal audit
    if protocol_dir and workflow:
        audit_warnings = audit_journal(protocol_dir, workflow)
        if audit_warnings:
            warning_lines = ["[JOURNAL AUDIT]"] + [f"  - {w}" for w in audit_warnings]
            parts.append("\n".join(warning_lines))

    # Knowledge gate prompt
    parts.append(
        "[KNOWLEDGE GATE] Before ending this session, invoke "
        'Skill(skill="panther-ivy-plugin:knowledge-capture") to capture '
        "any learnings from this session. If no learnable patterns are "
        "found, the skill exits silently."
    )

    return "\n".join(parts)


def main():
    read_stdin()  # consume stdin

    ivy_files = find_modified_ivy_files()
    if not ivy_files:
        sys.exit(0)

    ctx = WorkflowContext.current()
    workflow = ctx.workflow if ctx else None
    phase = ctx.phase if ctx else None
    protocol_dir = ctx.protocol_dir if ctx else None

    summary = build_summary(ivy_files, workflow, phase, protocol_dir)
    emit_hook_output("Stop", additional_context=summary)


if __name__ == "__main__":
    main()
