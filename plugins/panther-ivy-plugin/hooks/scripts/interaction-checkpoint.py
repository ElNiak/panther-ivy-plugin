#!/usr/bin/env python3
"""PostToolUse hook: inject interaction checkpoint reminders after key MCP tool results.

Reads tool output from stdin JSON. If the tool result indicates a situation
where user interaction is valuable (verification failure, coverage gaps, etc.),
outputs additionalContext prompting the agent to engage the user.

Non-blocking — always exits 0. Only injects reminders, never blocks tool use.
"""

import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_output = data.get("tool_output", "")

    # Normalize: tool_output may be a dict or string
    if isinstance(tool_output, dict):
        output_str = json.dumps(tool_output)
    else:
        output_str = str(tool_output)

    reminder = check_for_interaction(tool_name, output_str)

    if reminder:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": reminder,
            }
        }
        json.dump(result, sys.stdout)

    sys.exit(0)


def check_for_interaction(tool_name: str, output: str) -> str | None:
    """Check if the tool result warrants an interaction checkpoint reminder."""

    # ivy_verify failure → verification claim discussion
    if "ivy_verify" in tool_name:
        if any(kw in output.lower() for kw in [
            "fail", "error", "violated", "counterexample", "not safe",
        ]):
            return (
                "[INTERACTION CHECKPOINT] ivy_verify failure detected. "
                "Before proceeding, discuss this result with the user using the "
                "Verification Claim Discussion template from the `claim-discussion` skill. "
                "Present the counterexample, ask if the violated assertion is correct per the RFC, "
                "and resolve before moving on."
            )

    # ivy_coverage gaps → coverage gap discussion
    if "ivy_coverage" in tool_name:
        lower = output.lower()
        has_gap_keywords = any(kw in lower for kw in [
            "uncovered", "gap", "missing", "unguarded",
        ])
        # Match "0%" but not "100%" — look for non-digit before 0%
        has_zero_pct = " 0%" in lower or ":0%" in lower or '"0%"' in lower
        if has_gap_keywords or has_zero_pct:
            return (
                "[INTERACTION CHECKPOINT] Coverage gaps detected. "
                "Before proceeding, discuss these gaps with the user using the "
                "Coverage Gap Claim Discussion template from the `claim-discussion` skill. "
                "Present the gap summary, ask which gaps to prioritize, and "
                "check if any requirements are not applicable."
            )

    # ivy_extract_requirements → RFC mapping discussion
    if "ivy_extract_requirements" in tool_name:
        if any(kw in output.lower() for kw in [
            "must", "should", "may", "requirement", "normative",
        ]):
            return (
                "[INTERACTION CHECKPOINT] RFC requirements extracted. "
                "Before writing monitors, discuss each requirement mapping with the user "
                "using the RFC Mapping Claim Discussion template from the `claim-discussion` skill. "
                "Present the requirement text, proposed Ivy mapping, and confirm before proceeding."
            )

    # ivy_quality gate failure → quality discussion
    if "ivy_quality" in tool_name:
        if any(kw in output.lower() for kw in [
            "fail", "below", "not met", "gate_result.*fail",
        ]):
            return (
                "[INTERACTION CHECKPOINT] Quality gate check completed with issues. "
                "Discuss the quality findings with the user before proceeding. "
                "Present the quality summary and ask which improvements to prioritize."
            )

    return None


if __name__ == "__main__":
    main()
