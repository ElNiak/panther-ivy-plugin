---
name: build
description: "Use when starting a new protocol spec, scaffolding a new Ivy layer, or resuming an in-progress build. Multi-session construction from an RFC to a formal Ivy model."
---

<role>
You are the build workflow for the panther-ivy-plugin. Your job is to carry
a protocol model from RFC to a structurally sound, verified Ivy
specification layer by layer. You dispatch `spec-analyst` for compile-error
diagnosis, `model-reviewer` and `traceability-agent` for the Phase 5
quality and coverage audits, and MPE Explore agents at Phase 1 for
architectural-approach exploration. You are bound by the
`NO_LAYER_WITHOUT_SCAFFOLD` and `STALENESS_RULE` iron laws.
</role>

## Phase 0 — Plan-mode preamble

If the session is in plan mode, follow the 5-step authoring procedure in `.claude/rules/plan-mode.md`. Build-specific `AskUserQuestion` option framings for Step 2 (situation briefing): "draft a plan for the new layer we need", "draft a plan to restructure the blueprint", "clarify the modeling scope before writing", "learn the 14-layer template first".

## Iron Laws

This skill is bound by <iron-law name="NO_LAYER_WITHOUT_SCAFFOLD" workflow="build" enforcement="ivy_diagnostics precondition in Phase 3"/> and <iron-law name="STALENESS_RULE" workflow="build" enforcement="ivy_analysis(mode=includes) closure + tool result timestamp"/>. Before starting Phase 3 (Implement), Read `.claude/rules/iron-laws.md` for the canonical wording, the explicit "Out of scope" carve-outs (patches to existing layers, files outside `{prot}_stack/`, drafts outside discovery path), and the plan-mode exemption clause. Summary for this skill: ground each net-new layer file in a passing `ivy_diagnostics(mode="structural")` for the prior layer; treat any tool result older than the most recent edit to a file in the include closure as stale.

## Step Tracking

At the start of each phase, create tasks for each step using `TaskCreate`. Mark each `in_progress` before executing and `completed` after.

Phase 1 (Scope):
```
TaskCreate(subject="Detect methodology context", activeForm="Detecting methodology")
TaskCreate(subject="Identify target protocol and RFC", activeForm="Identifying target")
TaskCreate(subject="Confirm scope with user", activeForm="Confirming scope")
```

Phase 3 (Implement) — per layer:
```
TaskCreate(subject="Scaffold layer N: {layer_name}", activeForm="Scaffolding layer N")
TaskCreate(subject="Structural check on layer N", activeForm="Checking layer N structure")
TaskCreate(subject="Verify layer N with ivy_verify", activeForm="Verifying layer N")
```

Agent dispatch with dependencies (Phase 5):
```
TaskCreate(subject="Quality audit (model-reviewer)")        → task A
TaskCreate(subject="Coverage audit (traceability-agent)")   → task B
TaskUpdate(taskId=B, addBlockedBy=[A])
```

Mark each task `completed` as soon as it finishes. Incomplete tasks stay visible to the user and read as unfinished work.

## Process Flow

```dot
digraph build_flow {
  "Read active-workflow" -> "Phase 1: Scope";
  "Phase 1: Scope" -> "Phase 2: Blueprint";
  "Phase 2: Blueprint" -> "Phase 3: Implement layer N";
  "Phase 3: Implement layer N" -> "Structural check" [label="layer written"];
  "Structural check" -> "Fix + recheck" [label="FAIL"];
  "Fix + recheck" -> "Structural check";
  "Structural check" -> "ivy_verify" [label="PASS"];
  "ivy_verify" -> "Fix + re-verify" [label="FAIL"];
  "Fix + re-verify" -> "ivy_verify";
  "ivy_verify" -> "More layers?" [label="PASS"];
  "More layers?" -> "Phase 3: Implement layer N" [label="yes"];
  "More layers?" -> "Phase 5: Quality gate" [label="no"];
  "Phase 5: Quality gate" -> "Phase 6: Completion Verification Gate";
  "Phase 6: Completion Verification Gate" -> "Return to navigate";
}
```

# Build Workflow

Read `.panther-ivy/active-workflow` on every turn to determine the current phase. Update the phase field on transition.

## Adversarial Quality Gates

This workflow fires three adversarial quality gates during its lifecycle. Each gate dispatches context-isolated critics with verbatim prompts from the `reflection-patterns` skill and produces a calibrated verdict (`SOUND` / `UNSOUND(#NN, …)` / `ABSTAIN`) persisted to the workflow journal as a `gate_verdict` event.

| Gate | Fires | Artifact | Template |
|---|---|---|---|
| G1 exploration | After Phase 2 (blueprint), before Phase 3 | `build-state.yaml` + RFC scope | `reflection-patterns` → `critic_prompts/g1_exploration` |
| G2 modeling | PostToolUse on `Write\|Edit` of `*.ivy` (excluding `*_test_*.ivy`) during Phase 3 | The just-written layer file | `reflection-patterns` → `critic_prompts/g2_modeling` |
| G3 test-spec | PostToolUse on `Write\|Edit` of `*_test_*.ivy` during Phase 3 | The just-written test spec | `reflection-patterns` → `critic_prompts/g3_testspec` |

See `reflection-patterns` for the discipline contracts (verbatim prompts, dual context isolation, asymmetric vote, pigeonhole exit), the catalog pointer (`ivy-error-patterns` skill), and the `.claude/rules/gap-markers.md` convention for `[GAP: #NN]` markers the orchestrator writes on `UNSOUND` verdicts.

## Journal Requirements

Throughout this workflow, record state changes to the workflow journal:

- **Decisions**: When making or confirming a design/implementation choice (e.g., deferring a requirement, choosing layer order, selecting methodology), immediately call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="decision", state='{"summary": "<what was decided>", "context": "<why>"}')`

- **Progress**: After completing a meaningful sub-step (e.g., "compiled 3/8 layers", "fixed 2 verification failures"), call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="progress", state='{"detail": "<what completed>"}')`

These journal entries enable warm session resume and decision traceability across sessions.

---

## Phase 1 — Scope

### Step 1: Detect methodology context

Look for NCT/NACT/NSCT keywords in the user's request. If none found, ask: "Which testing methodology? NCT (compliance), NACT (security), or NSCT (simulation)."

Load the `methodology-reference` knowledge skill via the Skill tool for methodology details.

### Step 2: Identify target

Determine from the user's request or by asking:

- Protocol name (e.g., QUIC, BGP, CoAP)
- RFC number(s) to model
- Specific aspect or feature to target (e.g., "stream flow control", "connection migration")

### Gate checkpoint

Confirm understanding before proceeding: "I'll build a [methodology] model for [protocol] targeting [RFC]. Correct?"

Wait for explicit confirmation.

### Multi-Perspective Exploration — Architectural Approach

After the user confirms the scope, load the `reflection-patterns` skill. Apply **Pattern B (Multi-Perspective Exploration)**:

- **Exploration question:** "What architectural approach should we use for this [protocol] model?"
- **Agents:**
  - **Conservative Architect** (Explore): Propose a comprehensive model covering all RFC MUST requirements with full invariant coverage. Prioritize correctness over speed.
  - **Pragmatic Engineer** (Explore): Propose a minimal viable model — only the layers needed for the first end-to-end test. Build incrementally.
  - **Adversarial Auditor** (Explore): Propose a security-focused model prioritizing attack surface coverage (NACT-relevant layers, edge cases, error paths).

The user's choice shapes the blueprint in Phase 2.

### Step 3: Update state

Update phase to `"scoped"` via `ivy_workflow_state(action="set", workflow="build", phase="scoped", protocol="<protocol>")`.

---

## Phase 2 — Blueprint

### Step 1: Load patterns

Load the `specification-patterns` knowledge skill via the Skill tool.

### Step 2: Scan existing specs

Look in `protocol-testing/{protocol}/` for what already exists:

```
Glob(pattern="*.ivy", path="protocol-testing/{protocol}/")
```

Check for existing `build-state.yaml`:

```
ivy_workflow_state(action="get_build", protocol="<protocol>")
```

### Step 3: Propose layer structure (methodology-conditional)

Branch on the methodology detected in Phase 1, per `references/blueprint-methodology-choices.md`:

- **NCT** → the 14-layer template from `specification-patterns` (7-layer minimum viable set).
- **NACT** → NCT 7-layer prefix + multi-select `AskUserQuestion` for APT lifecycle, cross-cutting white_noise, attack entities.
- **NSCT** → NCT 7-layer verbatim; the Shadow-NS experiment-config sidecar is emitted at Phase 6, not Phase 2.

Record the chosen layers in `build-state.yaml.layers` with `status: pending`; Phase 3 writes each.

### Situation Briefing — Blueprint Approval

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)** as the gate checkpoint (do not proceed without explicit approval):

- **What happened:** Summarize the blueprint: how many layers proposed, which are new vs. reusable, estimated build order.
- **What it means:** Compare with the MPE recommendations from Phase 1 — which agent's approach was followed and why.
- **Options:** "Approve this blueprint and start writing" / "Adjust layer selection" / "Switch to a different architectural approach"

### Step 4: Write build state

Write `build-state.yaml` via `ivy_workflow_state(action="set_build", protocol="<protocol>", state="<JSON>")`:

```yaml
workflow: build
protocol: {protocol}
methodology: {nct|nact|nsct}
started: {ISO datetime}
layers:
  {layer_name}: { status: pending, file: {filename} }
  ...
decisions:
  - "reason for layer choices"
```

### Step 5: Update state

Update phase to `"blueprint-done"` via `ivy_workflow_state(action="set", workflow="build", phase="blueprint-done", protocol="<protocol>")`.

### G1 Exploration Gate

After the phase is set to `"blueprint-done"`, the G1 exploration gate fires (either via the `route-user-prompt.py` hook's post-blueprint branch or by the workflow inline invoking `reflection-patterns` Pattern B with the G1 verbatim template). Proceed to Phase 3 only on `VERDICT_SOUND`. On `VERDICT_UNSOUND`, resolve the cited `[GAP: #NN]` markers in `build-state.yaml` or the scope notes and re-run the gate. On `VERDICT_ABSTAIN`, surface the abstention reason and decide: collect more evidence, escalate to Opus tier, or accept + promote relevant GAPs to `// DEFERRED` before proceeding.

---

## Phase 3 — Write

Load `references/layer-scaffolding.md` for the full per-layer scaffolding procedure — including the compile-attempt cap (journal-counted, 5-per-layer cumulative across sessions, soft-reset via `override_attempt_cap` decision) and the post-edit workspace-block recovery menu. Summary of the scaffolding loop:

1. Load `ivy-writing-guide` skill.
2. Write ONE layer at a time in dependency order; run `ivy_compile` after each.
3. On compile error: dispatch `spec-analyst`, fix inline, recompile. The attempt-counter gate applies before each compile (see the reference for the 5-per-layer protocol, the journal-key canonicalization rule, and the three-option escalation menu — Continue anyway / Abandon this layer / Switch workflow).
4. On compile success: update `build-state.yaml` layer status.
5. Reflection Gate every 3 layers.
6. Handle type propagation via `propagation-patterns` skill if needed.
7. Knowledge Gate on completion of all layers.

### Post-Edit Workspace-Block Recovery

If a `Write`/`Edit` on a `.ivy` file is blocked by the `check-workspace-scope.py` PreToolUse hook (workspace-scope violation), follow the three-option recovery menu — switch workspace / clear workspace / abandon this layer — detailed in `references/layer-scaffolding.md` under "Post-Edit Workspace-Block Recovery". Each option updates `build-state.yaml.layers` or the journal as specified there. This path only fires when the harness propagates hook-block signals into the tool-result.

### G2 / G3 Gates Fire Per-File

After each `Write`/`Edit` on a `.ivy` file, a PostToolUse hook spawns critics from the `reflection-patterns` skill:
- `*.ivy` (non-test): G2 modeling critics (catalog slice `#200-249` + `#250-299` + NSCT `#260-289`).
- `*_test_*.ivy`: G3 test-spec critics (catalog slice `#200-208` + `#256-259` + `#300-399`).

On `VERDICT_UNSOUND`, the orchestrator writes `[GAP: #NN <reason>]` markers inline at the cited locations. Before starting the next layer, resolve every `[GAP:]` marker open across the current Phase 3 lifecycle — not just markers from the most recent write. Each marker is either fixed in place or deliberately promoted to `// DEFERRED YYYY-MM-DD: …` per `.claude/rules/gap-markers.md`. On `VERDICT_ABSTAIN`, the verdict lands silently in the workflow journal; read it at the next Reflection Gate.

---

## Phase 4 — Verify

Hand control to the `verify` workflow via a `pending_dispatch` event — no in-place state mutation, no direct `Skill(...)` invocation:

1. Append the dispatch:
   ```
   append_pending_dispatch(
     protocol="<protocol>",
     target_workflow="verify",
     reason="build Phase 4 — post-modeling verification"
   )
   ```
2. Clear the active-workflow flag: `ivy_workflow_state(action="clear", protocol="<protocol>")`.
3. End Phase 4. Build's turn is finished.

Navigate's Phase 1 Step 2c consumes the `pending_dispatch` on the next turn (or same-turn if the harness routes in-line) and dispatches `verify`. Verify runs its full cycle — including Phase 5 IUT testing, which now runs unconditionally because the cluster-1 refactor removed its `invocation_depth > 0` skip guard. On completion verify emits `pending_dispatch(build, phase_hint="quality-gate")` so build re-activates at Phase 5 on the following turn.

Build's Phase 5 reads the most recent `gate_verdict` (G4, G5) and `progress` journal entries to learn verify's outcome — the journal is the data bus between workflow frames; no shared memory besides `build-state.yaml`. If verify failed and the user chose to abandon rather than loop, the absence of a `pending_dispatch(build)` from verify is the signal to stop; build's re-entry then surfaces a summary and either returns to navigate or prompts the user.

---

## Phase 5 — Quality Gate

### Step 1: Dispatch review agents in parallel

Dispatch both agents in a single message using two Agent tool calls:

<dispatch target="model-reviewer" via="agent" phase="5"
          reason="Phase 5 quality audit — structural correctness, type safety, invariant completeness, action well-formedness, initialization, organization"/>

<dispatch target="traceability-agent" via="agent" phase="5"
          reason="Phase 5 coverage audit — RFC coverage check against the blueprint's target RFC(s)"/>

Sequencing: the `Agent(...)` calls go in a single message so the two
agents run in parallel. Classify their combined findings per Step 2.

### Step 2: Aggregate findings

Collect findings from both agents. Classify by severity per
`.claude/rules/ivy-formatting.md` Severity Systems ("Finding severity"):
<severity class="finding" value="ERROR"/> /
<severity class="finding" value="WARNING"/> /
<severity class="finding" value="INFO"/>.

### Gate checkpoint on ERROR findings

<checkpoint type="gate" id="phase-5-error-findings">
If any <severity class="finding" value="ERROR"/> findings are produced,
present them to the user: "These ERRORs were found: [list]. Fix them now?
Or accept and move on?" Wait for explicit confirmation.
</checkpoint>

### Step 3: Handle fixes

If the user wants fixes:

- For structural issues (type safety, invariants, initialization): loop back to Phase 3 to fix the affected layers.
- For verification issues (failed properties, counterexamples): loop back to Phase 4 to re-verify.
- For coverage gaps: add missing monitors inline, then re-run the traceability check.

### Situation Briefing — Quality Gate Results

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)**:

- **What happened:** Summarize the quality gate results: how many findings by severity (critical/important/suggestion), which agents found what, overall model health.
- **What it means:** Are ERROR-severity findings blocking? Is coverage sufficient for the target methodology?
- **Options:**
  - "Fix ERROR findings now" (if any exist)
  - "Proceed to wrap-up — accept current quality level"
  - "Run full verification before wrapping up"
  - "Review coverage gaps in detail"

### Step 4: Update state

Update phase to `"quality-passed"` via `ivy_workflow_state(action="set", workflow="build", phase="quality-passed", protocol="<protocol>")`.

### Knowledge Gate: Post-Quality-Gate

**KNOWLEDGE GATE (KG)**: Pause and invoke: `Skill(skill="panther-ivy-plugin:knowledge-capture")`
- Reflect on architecture decisions solidified during quality review
- Capture model-reviewer and traceability-agent findings worth remembering
- Save session log (observability events + digest)
- If candidates found, classify and present for user confirmation
- Resume workflow after gate completes

---

## Phase 6 — Wrap-up

Before completing, apply **Pattern D (Completion Verification Gate)** from the `reflection-patterns` skill.

### Step 1: Summarize

Present a summary of what was built:

- Layers completed (with file paths)
- Verification status (pass/fail per test)
- Coverage statistics (MUST/SHOULD/MAY covered)
- Key design decisions recorded in `build-state.yaml`

### Step 1b: NSCT sidecar emission (methodology-conditional)

If `build-state.yaml.methodology == "nsct"`, load `methodology-reference` skill and follow its `references/nsct-experiment-template.md` — substitute placeholders from `build-state.yaml`, `mkdir -p experiment-config/protocols/{protocol}/`, and write `experiment_config_{protocol}_shadow.yaml`. Append `progress{detail: "NSCT experiment-config scaffolded at <path>"}`. The sidecar is a scaffold, not runnable; users hand-edit topology, services, and IUT plugin names before running it. Skip entirely for `nct` or `nact`.

### Step 2: Clear state

If this build run needs another workflow to run next (e.g., user explicitly asked for a review after the quality gate), append `pending_dispatch(<next>, reason=<why>)` first. Then clear the active-workflow flag via `ivy_workflow_state(action="clear", protocol="<protocol>")`. Navigate's Phase 1 Step 2c consumes any pending dispatch on the next user turn. If no hand-off is needed, simply clear the flag — navigate re-activates on the next user turn and offers context-appropriate next steps based on the completed build.

---

## Multi-Session State

`build-state.yaml` is the persistence mechanism for multi-session builds:

- **Written at:** Phase 2 (blueprint)
- **Updated during:** Phase 3 (layer statuses set to `"complete"` as each layer compiles)
- **Read on resume:** Navigate reads this file in its warm-resume branch (Branch A) and dispatches back to build at the appropriate phase

On session resume, actual progress is inferred from the file system: which `.ivy` files exist, combined with the layer statuses in `build-state.yaml`. The phase field in `active-workflow` indicates which phase to resume from.

---

## Background Compilation

When `ivy_compile` would block for minutes, run it in a background subagent via `Agent(run_in_background: true, ...)` while productive work (next layer's scaffold, other-layer reviews, diagnostics) continues in the main conversation. On completion, integrate: SUCCESS → update `build-state.yaml` and proceed; FAILURE → dispatch `spec-analyst` synchronously. The staleness rule applies: re-run if the source `.ivy` was edited since the background run started. Full when-to-use, spawn prompt template, and during-the-wait guidance: `references/background-compilation.md`.

---

## Integration

- **Called by:** `navigate` (dispatch), user directly ("build a model", "scaffold a protocol")
- **Shortcut command alternative:** `/nct-compile <file>` for a single-shot layer compile without workflow state; see `commands/README.md` for the full shortcut catalog.
- **Calls:** `verify` (post-build verification), `spec-analyst` agent (compile error diagnosis), `model-reviewer` agent (quality gate), `traceability-agent` agent (coverage gate)
- **Knowledge skills loaded:** `reflection-patterns` (MPE Phase 1, SB Phase 2, RG Phase 3, SB Phase 5), `methodology-reference` (Phase 1), `specification-patterns` (Phase 2), `ivy-writing-guide` (Phase 3), `counterexample-guide` (Phase 3 on error), `propagation-patterns` (Phase 3 on type change), `knowledge-capture` (KG Phase 3, KG Phase 5)
- **MCP tools used:** `ivy_compile`, `ivy_workspace`
- **State files:** `.panther-ivy/active-workflow`, `.panther-ivy/build-state.yaml`
- **MCP tool reliability:** on `InputValidationError` from `ivy_compile` / `ivy_workspace`, follow `.claude/rules/mcp-tool-reliability.md` — one retry via `ToolSearch({query: "select:<tool>"})`, then AskUserQuestion with triage / skip / abandon options.
- **Agent dispatch:** build dispatches `spec-analyst` (Phase 3 compile-error diagnosis), `model-reviewer` + `traceability-agent` (Phase 5 quality gate, in parallel), and MPE Explore agents (Phase 1 architectural approach). On dispatch failure follow `.claude/rules/agent-dispatch.md`. Per-agent Failure Modes sections override default budgets — notably `model-reviewer`'s Opus tier (180 s) and no-auto-retry-on-context-exhaustion.
