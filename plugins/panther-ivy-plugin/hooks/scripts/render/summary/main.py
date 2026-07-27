#!/usr/bin/env python3
"""Stop hook: workflow-aware session summary.

Replaces stop-session-summary.sh. Absorbs all existing functionality (lint
scan, claim counts, tool metrics) and routes through workflow-specific
summary templates.

Non-blocking -- always exits 0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.hook_utils import emit_hook_output, emit_noop, is_session_active, read_stdin
from lib.workflow_state import WorkflowContext, get_scaffold_state_safe
from render.summary.helpers import (
    CLAIM_PATTERNS,
    audit_journal,
    check_lint,
    count_claims,
    find_modified_ivy_files,
    gather_tool_metrics,
)


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

    # Build state (for scaffold workflow)
    scaffold_state = None
    if workflow == "scaffold" and protocol_dir:
        scaffold_state = get_scaffold_state_safe(protocol_dir)

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
    if workflow == "refine":
        if phase:
            parts.append(f"[WORKFLOW] Refine workflow ended in phase: {phase}")

    elif workflow == "experiment":
        if phase:
            parts.append(f"[WORKFLOW] Experiment workflow ended in phase: {phase}")

    elif workflow == "scaffold" and scaffold_state:
        layers = scaffold_state.get("layers", {})
        if layers:
            layer_lines = ["[SCAFFOLD PROGRESS]"]
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

    return "\n".join(parts)


def main():
    read_stdin()  # consume stdin

    if not is_session_active():
        emit_noop("Stop", "no ivy activity this session")
        return

    ivy_files = find_modified_ivy_files()
    if not ivy_files:
        emit_noop("Stop", "no .ivy files modified this session")
        return

    ctx = WorkflowContext.current()
    workflow = ctx.workflow if ctx else None
    phase = ctx.phase if ctx else None
    protocol_dir = ctx.protocol_dir if ctx else None

    summary = build_summary(ivy_files, workflow, phase, protocol_dir)
    emit_hook_output("Stop", system_message=summary)


if __name__ == "__main__":
    main()
