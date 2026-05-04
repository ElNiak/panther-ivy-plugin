#!/usr/bin/env python3
"""PostToolUse hook: reformat MCP tool results per active workflow style.

Reads tool output from stdin JSON. For the 5 rendered tools (ivy_verify,
ivy_coverage, ivy_diagnostics, ivy_compile, ivy_quality), reformats the
result according to the active workflow's style rules and outputs as
hookSpecificOutput.

Non-blocking -- always exits 0.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.hook_utils import emit_hook_output, emit_noop, read_stdin
from lib.workflow_state import WorkflowContext

RENDERED_TOOLS = {
    "ivy_verify",
    "ivy_coverage",
    "ivy_diagnostics",
    "ivy_compile",
    "ivy_quality",
}


def _match_tool(tool_name: str) -> str | None:
    """Extract the base tool name if it matches a rendered tool."""
    for rendered in RENDERED_TOOLS:
        if rendered in tool_name:
            return rendered
    return None


def _parse_output(raw: str | dict) -> dict:
    """Parse tool output into a dict. Returns empty dict on failure."""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


def _safe_get(data: dict, key: str, default: str = "?") -> str:
    """Get a value from dict, converting to str with a fallback."""
    val = data.get(key)
    return str(val) if val is not None else default


# -- Formatters --
# Each returns a formatted string or None (to skip formatting).


def format_ivy_verify(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "success" not in data:
        return None  # pass through errors

    success = data.get("success", True)
    isolate = _safe_get(data, "isolate", "unknown")
    clauses = _safe_get(data, "clause_count", "?")
    duration = _safe_get(data, "duration_s", "?")
    errors = data.get("errors", [])

    if workflow == "triage":
        if success:
            return "ivy_verify: OK"
        return f"ivy_verify: FAIL -- {len(errors)} error(s). Run refine workflow for details."

    if workflow == "scaffold":
        if success:
            return f"Layer verified: {isolate} PASS"
        return "Layer verification failed -- switching to refine workflow for diagnosis."

    if workflow == "review":
        status = "PASS" if success else "FAIL"
        return f"| {isolate} | {status} | {clauses} | {duration}s |"

    if workflow == "refine":
        if success:
            return f"PASS: {isolate} ({clauses} clauses, {duration}s)"
        lines = []
        for i, err in enumerate(errors, 1):
            f = err.get("file", "?")
            ln = err.get("line", "?")
            msg = err.get("message", "?")
            lines.append(f"{i}. FAIL: {isolate} at {f}:{ln} -- {msg}")
        return "\n".join(lines) if lines else f"FAIL: {isolate} -- verification failed"

    # default
    if success:
        return f"PASS: {isolate} verified ({clauses} clauses, {duration}s)"
    if errors:
        err = errors[0]
        return f"FAIL: {isolate} at {err.get('file', '?')}:{err.get('line', '?')} -- {err.get('message', '?')}"
    return f"FAIL: {isolate} -- verification failed"


def format_ivy_coverage(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "covered" not in data and "percentage" not in data:
        return None

    pct = _safe_get(data, "percentage", "?")
    covered = _safe_get(data, "covered", "?")
    total = _safe_get(data, "total", "?")

    if workflow == "triage":
        return f"Coverage: {pct}%"

    if workflow == "refine":
        return f"{pct}% ({covered}/{total})"

    if workflow == "review":
        sections = data.get("by_section", {})
        if sections:
            lines = ["| Section | Covered | Total | % |", "| --- | --- | --- | --- |"]
            for sec, vals in sections.items():
                sc = vals.get("covered", "?")
                st = vals.get("total", "?")
                sp = vals.get("percentage", "?")
                lines.append(f"| {sec} | {sc} | {st} | {sp}% |")
            lines.append(f"\n**Total**: {pct}% ({covered}/{total})")
            return "\n".join(lines)
        return f"{pct}% MUST coverage ({covered}/{total})"

    # default / build
    return f"{pct}% MUST coverage ({covered}/{total})"


def format_ivy_diagnostics(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "issues" not in data:
        return None

    issues = data.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    if workflow == "triage":
        return f"{len(errors)} errors, {len(warnings)} warnings"

    if workflow == "refine" or workflow == "review":
        lines = ["| Severity | File | Line | Message |", "| --- | --- | --- | --- |"]
        for issue in errors + warnings:
            sev = issue.get("severity", "?")
            f = issue.get("file", "?")
            ln = issue.get("line", "?")
            msg = issue.get("message", "?")
            lines.append(f"| {sev} | {f} | {ln} | {msg} |")
        return "\n".join(lines) if len(lines) > 2 else "No diagnostic issues found."

    # default / build
    lines = []
    for issue in errors + warnings:
        sev = issue.get("severity", "?").upper()
        f = issue.get("file", "?")
        ln = issue.get("line", "?")
        msg = issue.get("message", "?")
        lines.append(f"{sev}: {f}:{ln} -- {msg}")
    return "\n".join(lines) if lines else "No diagnostic issues found."


def format_ivy_compile(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "status" not in data:
        return None

    success = data.get("status") == "success" or data.get("success", False)
    binary = _safe_get(data, "output_binary", "?")
    duration = _safe_get(data, "duration_s", "?")
    err_msg = _safe_get(data, "error_message", data.get("error", "unknown error"))

    if workflow == "triage":
        return "ivy_compile: OK" if success else f"ivy_compile: FAIL -- {err_msg}"

    if workflow == "scaffold":
        if success:
            return f"Layer compiled: {binary}"
        return "Layer compilation failed. Fix before proceeding to next layer."

    if workflow == "refine":
        if success:
            return f"Compiled: {binary} ({duration}s)"
        return f"Compilation failed: {err_msg}. Consider switching to diagnose phase."

    # default / review
    if success:
        return f"Compiled -> {binary} ({duration}s)"
    return f"Compilation failed: {err_msg}"


def format_ivy_quality(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "suggestions" not in data and "passed" not in data:
        return None

    # Gate mode
    if "passed" in data or "gate_level" in data:
        passed = data.get("passed", False)
        level = _safe_get(data, "gate_level", "?")
        failures = data.get("failures", [])

        if workflow == "triage":
            if passed:
                return "Quality gate: PASS"
            return f"Quality gate: FAIL ({len(failures)})"

        if workflow == "refine":
            return f"Gate {level}: {'PASS' if passed else 'FAIL'}"

        if workflow == "review":
            lines = ["| Criterion | Status | Details |", "| --- | --- | --- |"]
            for f in failures:
                lines.append(f"| {f.get('criterion', '?')} | FAIL | {f.get('details', '?')} |")
            return "\n".join(lines) if len(lines) > 2 else f"Gate {level}: PASS"

        # default / build
        if passed:
            return f"Gate {level}: PASS"
        return f"Gate {level}: FAIL -- {len(failures)} issue(s)"

    # Suggestions mode
    suggestions = data.get("suggestions", [])
    if workflow in ("triage", "refine"):
        return None  # suppress suggestions in triage/refine

    lines = []
    for i, s in enumerate(suggestions, 1):
        cat = s.get("category", "?")
        msg = s.get("message", "?")
        sev = s.get("severity", "?")
        lines.append(f"{i}. [{sev}] {cat}: {msg}")
    return "\n".join(lines) if lines else "No quality suggestions."


FORMATTERS = {
    "ivy_verify": format_ivy_verify,
    "ivy_coverage": format_ivy_coverage,
    "ivy_diagnostics": format_ivy_diagnostics,
    "ivy_compile": format_ivy_compile,
    "ivy_quality": format_ivy_quality,
}


def main():
    data = read_stdin()
    tool_name = data.get("tool_name", "")
    base_tool = _match_tool(tool_name)
    if not base_tool:
        emit_noop("PostToolUse", f"unrecognized tool '{tool_name}'")
        return

    tool_output = _parse_output(data.get("tool_output", ""))
    if not tool_output:
        emit_noop("PostToolUse", f"{base_tool} produced no parseable output")
        return

    ctx = WorkflowContext.current()
    workflow = ctx.workflow if ctx else None

    formatter = FORMATTERS.get(base_tool)
    if not formatter:
        emit_noop("PostToolUse", f"no formatter registered for '{base_tool}'")
        return

    formatted = formatter(tool_output, workflow)
    if formatted:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-render] formatted {base_tool} result "
                f"for workflow={workflow or '<none>'}"
            ),
            additional_context=formatted,
        )
    else:
        emit_noop(
            "PostToolUse",
            f"{base_tool} formatter produced no output (workflow={workflow or '<none>'})",
        )


if __name__ == "__main__":
    main()
