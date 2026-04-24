#!/usr/bin/env python3
"""UserPromptSubmit hook: route user prompts to workflow skills via rules config."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from workflow_state import append_journal_event, find_protocol_dir, get_active_workflow

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
    active = None
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
    # emit an explicit continuation directive instead of going silent. Opus
    # 4.7 is literal about routing context; an affirmative "stay here" reads
    # better than silence when the hook has signal to share. Only route to
    # a different workflow when intent diverges or the user explicitly asks
    # to switch.
    if active_workflow_name and scored and not prompt_has_switch_intent(prompt_lower):
        best_names = [name for s, name in scored if s == scored[0][0]]
        if active_workflow_name in best_names:
            active_phase = active.get("phase") if active else None
            phase_suffix = f" phase='{active_phase}'" if active_phase else ""
            emit_hook_output(
                "UserPromptSubmit",
                additional_context=(
                    f"[ROUTING:CONTINUE] Staying in '{active_workflow_name}' "
                    f"workflow{phase_suffix}. Read .panther-ivy/active-workflow "
                    f"for phase detail before acting."
                ),
            )
            return

    # Record context switch when active workflow doesn't match best intent
    if active_workflow_name and scored and protocol_dir:
        best_names = [name for s, name in scored if s == scored[0][0]]
        if active_workflow_name not in best_names:
            append_journal_event(
                protocol_dir,
                event_type="context_switch",
                payload={
                    "away_from": active_workflow_name,
                    "reason": f"user intent matched: {best_names[0]}" if best_names else None,
                },
                workflow=active_workflow_name,
                phase=active.get("phase") if active else None,
            )

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

    # G1 exploration gate: fires when the build workflow is in phase
    # "blueprint-done". The directive below instructs Claude to dispatch G1
    # critics before advancing to Phase 3 (Write). Phase transition is the
    # idempotency mechanism — after Claude runs the gate and moves phase
    # forward, subsequent UserPromptSubmit turns will not re-emit the
    # directive.
    if active_workflow_name == "build" and active and active.get("phase") == "blueprint-done":
        if protocol_dir:
            append_journal_event(
                protocol_dir,
                event_type="gate_dispatched",
                payload={
                    "gate": "g1",
                    "trigger": "route-user-prompt.py",
                },
                workflow="build",
                phase=active.get("phase"),
            )
        parts.append(
            "[G1 exploration gate] Build phase is `blueprint-done`. Before advancing to Phase 3 (Write), "
            "dispatch the G1 exploration gate: (1) load the `reflection-patterns` skill via the Skill tool, "
            "(2) read the G1 verbatim critic template at `critic_prompts/g1_exploration.md` within that skill, "
            "(3) apply the discipline-layer rules (verbatim prompts, dual context isolation, asymmetric vote "
            "3-of-3 for Opus default / 4-of-5 for Sonnet, pigeonhole exit, calibrated abstention), "
            "(4) each critic must load the `ivy-error-patterns` skill and apply ID ranges #100-149 + "
            "#150-199 (if NACT) + #250-299, (5) aggregate into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN, "
            "(6) on UNSOUND write `[GAP:]` markers per `.claude/rules/gap-markers.md` (use `# [GAP: …]` "
            "YAML-comment form when annotating `build-state.yaml`; never insert bare `[GAP:]` tokens into "
            "YAML structure), (7) append a `gate_verdict` event to the workflow journal via "
            "`ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`, "
            "(8) render the verdict block per `styles/tool-renderers/ivy_verdict.md`. Only advance the build "
            "phase past `blueprint-done` on VERDICT_SOUND."
        )

    if not parts:
        return

    emit_hook_output("UserPromptSubmit", additional_context="\n".join(parts))


if __name__ == "__main__":
    main()
