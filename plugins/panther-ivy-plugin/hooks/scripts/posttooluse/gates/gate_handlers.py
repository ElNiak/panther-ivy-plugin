#!/usr/bin/env python3
"""Per-gate handler functions for the parametric G-gate runner.

Each gate (g2, g3, g5) provides three handlers — `parse_<id>`,
`predicate_<id>`, `dispatch_<id>` — referenced from the GATES
registry in `registry.py` and orchestrated by `run-gate.py`. Handlers
communicate via a single `ctx` dict the runner threads through:

    run-gate: tool_name in watched_tools  →  parse_<id>(hook_input) → ctx
                                          →  predicate_<id>(ctx)
                                          →  workflow gate (if workflow_required)
                                          →  set ctx["protocol_dir"] + ctx["workflow_ctx"]
                                          →  dispatch_<id>(ctx)

Each `dispatch_<id>` owns the per-gate `additionalContext` directive,
the `gate_dispatched` journal payload shape, and the user-visible T2
`systemMessage`. Bodies are lifted (where possible) from the pre-PR3
dispatchers (`g2-modeling.py`, `g3-testspec.py`, `g5-trace.py`) so the
existing test assertions on the directive prose and journal payloads
continue to hold.

Why dispatch is one function per gate (not parameterized):
- G2/G3 systemMessage prefixes differ (`[G2 modeling gate]` vs
  `[G3 test-spec gate]`); G5 uses `run_id` instead of basename.
- G2 payload includes `layer`; G3 omits it; G5 nests an `artifacts`
  dict.
- G5's directive embeds `must NOT invoke ivy_iut_test`, the others
  do not.
- Workflow-context resolution differs: G2/G3 read it from
  `WorkflowContext.current()` (set by the runner into ctx); G5
  reads it from `get_active_workflow(protocol_dir)` because
  `ivy_iut_test` invocations have no `WorkflowContext.current()`.

The discipline tests (`test_hook_output_discipline.py`,
`test_observability_write_discipline.py`) AST-scan each
state-writing hook for an f-string `systemMessage` that matches T2
(`"... appended to journal at <path>"`) and a `journal_path(...)`
call. Each `dispatch_<id>` below contains both, satisfying the
discipline.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.hook_utils import emit_hook_output
from lib.workflow_state import (
    append_journal_event,
    get_active_workflow,
    get_scaffold_state_safe,
    journal_path,
)


# ---------------------------------------------------------------- helpers


def _is_layer_file(file_path: str) -> bool:
    """True for .ivy files that are NOT test specs."""
    if not file_path.endswith(".ivy"):
        return False
    name = os.path.basename(file_path)
    return "_test_" not in name and not name.endswith("_test.ivy")


def _is_test_spec(file_path: str) -> bool:
    """True for .ivy files that are test specs (name contains `_test_` or ends `_test.ivy`)."""
    if not file_path.endswith(".ivy"):
        return False
    name = os.path.basename(file_path)
    return "_test_" in name or name.endswith("_test.ivy")


def _resolve_layer_from_scaffold_state(
    file_path: str,
    scaffold_state: "dict[str, Any] | None",
) -> Optional[str]:
    """Resolve layer name from scaffold-state.yaml `layers` map, if available."""
    if not scaffold_state:
        return None
    layers = scaffold_state.get("layers") or {}
    target = os.path.basename(file_path)
    for name, entry in layers.items():
        if isinstance(entry, dict) and os.path.basename(entry.get("file", "")) == target:
            return name
    return None


def _parse_tool_result(raw: object) -> "dict[str, Any] | None":
    """Parse a tool_result into a dict, whether it is already a dict or a JSON string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def _resolve_workflow_phase(
    workflow_ctx: object,
    protocol_dir: Optional[str],
) -> "tuple[str | None, str | None]":
    """Resolve (workflow, phase) from ctx['workflow_ctx'] or active-workflow YAML."""
    if workflow_ctx is not None:
        return workflow_ctx.workflow, workflow_ctx.phase  # type: ignore[attr-defined]
    if protocol_dir:
        state = get_active_workflow(protocol_dir) or {}
        return state.get("workflow"), state.get("phase")
    return None, None


# ---------------------------------------------------------------- G2 (modeling)


def parse_g2(hook_input: dict) -> Optional[dict]:
    """Extract the file path under audit. Return None if missing."""
    tool_input = hook_input.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None
    return {"file_path": file_path}


def predicate_g2(ctx: dict) -> bool:
    """G2 fires only on layer files (excludes test specs)."""
    return _is_layer_file(ctx["file_path"])


def dispatch_g2(ctx: dict) -> None:
    """Build payload + directive, append journal, emit hook output (T2 systemMessage)."""
    file_path = ctx["file_path"]
    protocol_dir = ctx.get("protocol_dir") or ""
    workflow_ctx = ctx.get("workflow_ctx")

    scaffold_state = get_scaffold_state_safe(protocol_dir) or {} if protocol_dir else {}
    protocol = (
        scaffold_state.get("protocol")
        or (os.path.basename(protocol_dir.rstrip("/")) if protocol_dir else "<unknown>")
    )
    methodology = scaffold_state.get("methodology")
    layer_name = _resolve_layer_from_scaffold_state(file_path, scaffold_state)

    if protocol_dir:
        workflow, phase = _resolve_workflow_phase(workflow_ctx, protocol_dir)
        append_journal_event(
            protocol_dir,
            event_type="gate_dispatched",
            payload={
                "gate": "g2",
                "trigger": "run-gate.py --id g2",
                "artifact": file_path,
                "layer": layer_name,
                "methodology": methodology,
            },
            workflow=workflow,
            phase=phase,
        )

    layer_line = (
        f"- Layer (from scaffold-state.yaml): {layer_name}"
        if layer_name
        else "- Layer: unknown — not resolved from scaffold-state.yaml"
    )
    methodology_line = (
        f"- Methodology: {methodology}"
        if methodology
        else "- Methodology: unknown (NACT/NSCT overlays not applied)"
    )
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: include catalog range #260-289 in the slice."

    directive = (
        "[G2 modeling gate] An .ivy layer file has been written while the `scaffold` workflow is active. "
        "Dispatch the G2 modeling gate before proceeding to the next layer.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{layer_line}\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G2 verbatim critic template at `skills/ivy/references/critic_prompts/g2_modeling.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #200-249 + #250-299 (+ #260-289 if NSCT).\n"
        "4. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "5. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only — never let a critic edit the file).\n"
        "6. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "7. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the scaffold-overlay format.\n\n"
        "Do not proceed to the next layer until each `[GAP:]` is either resolved or deliberately promoted to `// DEFERRED YYYY-MM-DD: …`."
    )

    suffix = (
        f"; gate_dispatched appended to journal at {journal_path(protocol_dir)}"
        if protocol_dir
        else ""
    )
    emit_hook_output(
        "PostToolUse",
        system_message=f"[G2 modeling gate] dispatched on {os.path.basename(file_path)}{suffix}",
        additional_context=directive,
    )


# ---------------------------------------------------------------- G3 (test-spec)


def parse_g3(hook_input: dict) -> Optional[dict]:
    """Extract the test-spec file path under audit. Return None if missing."""
    tool_input = hook_input.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None
    return {"file_path": file_path}


def predicate_g3(ctx: dict) -> bool:
    """G3 fires only on test-spec files."""
    return _is_test_spec(ctx["file_path"])


def dispatch_g3(ctx: dict) -> None:
    """Build payload + directive, append journal, emit hook output (T2 systemMessage)."""
    file_path = ctx["file_path"]
    protocol_dir = ctx.get("protocol_dir") or ""
    workflow_ctx = ctx.get("workflow_ctx")

    scaffold_state = get_scaffold_state_safe(protocol_dir) or {} if protocol_dir else {}
    protocol = (
        scaffold_state.get("protocol")
        or (os.path.basename(protocol_dir.rstrip("/")) if protocol_dir else "<unknown>")
    )
    methodology = scaffold_state.get("methodology")

    if protocol_dir:
        workflow, phase = _resolve_workflow_phase(workflow_ctx, protocol_dir)
        append_journal_event(
            protocol_dir,
            event_type="gate_dispatched",
            payload={
                "gate": "g3",
                "trigger": "run-gate.py --id g3",
                "artifact": file_path,
                "methodology": methodology,
            },
            workflow=workflow,
            phase=phase,
        )

    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: NSCT-specific test-spec patterns are limited; apply base catalog slice only."

    directive = (
        "[G3 test-spec gate] A `*_test_*.ivy` file has been written while the `scaffold` workflow is active. "
        "Dispatch the G3 test-spec gate before running `ivy_compile` / `ivy_verify`.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G3 verbatim critic template at `skills/ivy/references/critic_prompts/g3_testspec.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #200-208 + #256-259 + #300-399.\n"
        "4. Before spawning critics, gather inputs the template expects: the test file contents, the RFC requirement manifest (typically `{protocol}_requirements.yaml`), and the output of `ivy_coverage(mode=\"matrix\", test_file=<file_path>)`.\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only).\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the scaffold-overlay format.\n\n"
        "A test spec that looks clean but silently fails to cover a MUST requirement or over-constrains the generator is the exact failure mode G3 exists to catch — read the coverage matrix carefully."
    )

    suffix = (
        f"; gate_dispatched appended to journal at {journal_path(protocol_dir)}"
        if protocol_dir
        else ""
    )
    emit_hook_output(
        "PostToolUse",
        system_message=f"[G3 test-spec gate] dispatched on {os.path.basename(file_path)}{suffix}",
        additional_context=directive,
    )


# ---------------------------------------------------------------- G5 (trace-analysis)


def parse_g5(hook_input: dict) -> Optional[dict]:
    """Extract artifacts from ivy_iut_test tool_result. Return None if unparseable."""
    tool_result = _parse_tool_result(hook_input.get("tool_result"))
    if not tool_result:
        return None
    artifacts = {
        "output_dir": tool_result.get("output_dir", ""),
        "logs_path": tool_result.get("logs_path", ""),
        "pcap_path": tool_result.get("pcap_path", ""),
        "ivy_trace_path": tool_result.get("ivy_trace_path", ""),
        "protocol": tool_result.get("protocol", ""),
        "test": tool_result.get("test", ""),
        "iut": tool_result.get("iut", ""),
        "run_id": tool_result.get("run_id", ""),
        "summary": tool_result.get("summary", {}),
    }
    if not artifacts["output_dir"]:
        return None
    return {"artifacts": artifacts}


def predicate_g5(ctx: dict) -> bool:
    """G5 always fires once parse_g5 succeeded (output_dir non-empty was the parse gate)."""
    return bool(ctx.get("artifacts", {}).get("output_dir"))


def dispatch_g5(ctx: dict) -> None:
    """Build payload + directive, append journal, emit hook output (T2 systemMessage)."""
    artifacts = ctx["artifacts"]
    protocol_dir = ctx.get("protocol_dir") or ""
    workflow_ctx = ctx.get("workflow_ctx")  # always None for G5 (no workflow_required)

    scaffold_state = get_scaffold_state_safe(protocol_dir) or {} if protocol_dir else {}
    methodology = scaffold_state.get("methodology")

    if protocol_dir:
        workflow, phase = _resolve_workflow_phase(workflow_ctx, protocol_dir)
        append_journal_event(
            protocol_dir,
            event_type="gate_dispatched",
            payload={
                "gate": "g5",
                "trigger": "run-gate.py --id g5",
                "artifacts": {k: v for k, v in artifacts.items() if k != "summary"},
                "methodology": methodology,
            },
            workflow=workflow,
            phase=phase,
        )

    output_dir = artifacts.get("output_dir", "<unknown>")
    logs_path = artifacts.get("logs_path", "<unknown>")
    pcap_path = artifacts.get("pcap_path", "<unknown>")
    ivy_trace_path = artifacts.get("ivy_trace_path", "<unknown>")
    protocol = artifacts.get("protocol", "<unknown>")
    test = artifacts.get("test", "<unknown>")
    iut = artifacts.get("iut", "<unknown>")
    run_id = artifacts.get("run_id", "<unknown>")
    test_passed = artifacts.get("summary", {}).get("test_passed", "<unknown>")

    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: include catalog range #560-589 (replay/syscall) in the slice."

    directive = (
        f"[G5 trace-analysis gate] An `ivy_iut_test` run has completed ({protocol}/{test} against {iut}, run_id={run_id}, test_passed={test_passed}). "
        "Dispatch the G5 trace-analysis gate before accepting the run's verdict as ground truth.\n\n"
        "Artifact paths:\n"
        f"- `output_dir`: {output_dir}\n"
        f"- `logs_path`: {logs_path}\n"
        f"- `pcap_path`: {pcap_path}\n"
        f"- `ivy_trace_path`: {ivy_trace_path}\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G5 verbatim critic template at `skills/ivy/references/critic_prompts/g5_trace.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #100-107 + #500-559 (+ #560-589 if NSCT).\n"
        "4. CRITICAL constraint: critics must read the run output directory in the mandatory order (analysis_results.json → compile log if compilation suspect → ivy_tester.log → IUT log → pcaps via tshark). They must NOT invoke `ivy_iut_test` themselves — spawning a new run is forbidden.\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited spec file:line locations (not at artifact paths — the spec is the mutable target) per `.claude/rules/gap-markers.md`.\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the verify-overlay format.\n\n"
        "The hardest G5 call is distinguishing a real IUT bug from a model bug misattributed to the IUT. When in doubt about attribution, critics return UNSURE rather than bless an incorrect story."
    )

    suffix = (
        f"; gate_dispatched appended to journal at {journal_path(protocol_dir)}"
        if protocol_dir
        else ""
    )
    emit_hook_output(
        "PostToolUse",
        system_message=f"[G5 trace-analysis gate] dispatched on run_id={run_id}{suffix}",
        additional_context=directive,
    )
