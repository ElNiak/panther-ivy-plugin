#!/usr/bin/env python3
"""UserPromptSubmit hook: route user prompts to workflow skills via rules config."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from workflow_state import find_protocol_dir, get_active_workflow

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SWITCH_KEYWORDS = ("switch to", "cancel", "stop this", "something else")


def load_routing_rules() -> dict | None:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        return None
    path = os.path.join(plugin_root, "routing-rules.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def prompt_has_switch_intent(prompt_lower: str) -> bool:
    return any(kw in prompt_lower for kw in SWITCH_KEYWORDS)


def matches_file_triggers(prompt: str, triggers: list[str]) -> bool:
    for pattern in triggers:
        if pattern.startswith("*."):
            ext = pattern[1:]
            if re.search(r"\S+" + re.escape(ext) + r"(?:\s|$|[,;:)])", prompt):
                return True
    return False


def score_workflow(prompt: str, prompt_lower: str, config: dict) -> tuple[int, int]:
    """Return (priority_rank, match_quality) where lower is better.

    match_quality: 0 = intentPattern, 1 = fileTrigger, 2 = keyword-only.
    Returns (999, 999) for no match.
    """
    priority = PRIORITY_ORDER.get(config.get("priority", "low"), 3)
    best_quality = 999

    for pattern in config.get("intentPatterns", []):
        try:
            if re.search(pattern, prompt, re.IGNORECASE):
                best_quality = min(best_quality, 0)
                break
        except re.error:
            continue

    if best_quality > 1 and matches_file_triggers(prompt, config.get("fileTriggers", [])):
        best_quality = min(best_quality, 1)

    for kw in config.get("keywords", []):
        if kw.lower() in prompt_lower:
            best_quality = min(best_quality, 2)
            break

    if best_quality == 999:
        return (999, 999)
    return (priority, best_quality)


def check_learning_injection(prompt: str, prompt_lower: str, config: dict) -> list[str] | None:
    for kw in config.get("keywords", []):
        if kw.lower() in prompt_lower:
            return config.get("knowledge_skills", [])
    for pattern in config.get("intentPatterns", []):
        try:
            if re.search(pattern, prompt, re.IGNORECASE):
                return config.get("knowledge_skills", [])
        except re.error:
            continue
    return None


def main() -> None:
    hook_input = read_stdin()
    prompt = hook_input.get("prompt", "").strip()
    if not prompt:
        return

    rules = load_routing_rules()
    if not rules:
        return

    prompt_lower = prompt.lower()

    protocol_dir = find_protocol_dir()
    active_workflow_name = None
    if protocol_dir:
        active = get_active_workflow(protocol_dir)
        if active:
            active_workflow_name = active.get("workflow")

    workflows = rules.get("workflows", {})
    scored: list[tuple[tuple[int, int], str]] = []
    for name, config in workflows.items():
        score = score_workflow(prompt, prompt_lower, config)
        if score != (999, 999):
            scored.append((score, name))

    scored.sort(key=lambda x: x[0])

    # If an active workflow exists and the best match is the same workflow,
    # suppress routing (user is continuing current work). Only route when
    # intent diverges or the user explicitly asks to switch.
    if active_workflow_name and scored and not prompt_has_switch_intent(prompt_lower):
        best_names = [name for s, name in scored if s == scored[0][0]]
        if active_workflow_name in best_names:
            return

    learning_skills: list[str] | None = None
    learning_config = rules.get("learning_injection")
    if learning_config:
        learning_skills = check_learning_injection(prompt, prompt_lower, learning_config)

    # Learning injection suppresses workflow activation (spec: learning questions
    # are answered from knowledge skills, no workflow activation)
    matched_workflows: list[str] = []
    if not learning_skills and scored:
        best_score = scored[0][0]
        matched_workflows = [name for s, name in scored if s == best_score]

    if not matched_workflows and not learning_skills:
        # Fallback: if we're in an Ivy workspace with no active workflow and
        # no pattern matched, emit a lightweight reminder of available workflows.
        if protocol_dir and not active_workflow_name:
            emit_hook_output(
                "UserPromptSubmit",
                additional_context=(
                    "[ROUTING:AVAILABLE] Ivy workspace detected. "
                    "Available workflow skills: verify (test/debug), "
                    "build (create/extend model), review (coverage/quality), "
                    "triage (fix tools), navigate (guided routing). "
                    "Invoke the one matching the user's intent, or proceed without a workflow for simple tasks."
                ),
            )
        return

    parts: list[str] = []
    if matched_workflows:
        if len(matched_workflows) == 1:
            parts.append(f"[ROUTING] Activate the '{matched_workflows[0]}' workflow skill.")
        else:
            wf_list = "', '".join(matched_workflows)
            parts.append(
                f"[ROUTING] Multiple workflows match: '{wf_list}'. "
                f"Use the CLAUDE.md dispatch table to choose the best fit."
            )
    if learning_skills:
        skill_list = ", ".join(learning_skills)
        parts.append(f"[ROUTING:KNOWLEDGE] Load knowledge skills: {skill_list}")

    emit_hook_output("UserPromptSubmit", additional_context="\n".join(parts))


if __name__ == "__main__":
    main()
