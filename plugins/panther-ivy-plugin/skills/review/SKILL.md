---
name: review
description: "Quality and coverage auditing for Ivy models. Use when the user asks for coverage checks, quality audits, or model reviews."
---

## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
your active workflow overlay and phase modifier. Do not invent your own
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.

# Review Workflow

Read `.panther-ivy/active-workflow` on every turn to determine your current phase. Update the phase field as you transition.

---

## Phase 1 — Triage

### Step 1: Detect review type

Classify the user's intent into one of three review types:

| Review Type | Trigger Keywords |
|-------------|-----------------|
| **Coverage** | "RFC gaps", "how much do I cover", "coverage", "traceability", "requirements" |
| **Quality** | "review my model", "issues", "quality", "check for problems", "audit" |
| **Both** | Ambiguous request, or user explicitly asks for both |

### Step 2: Detect target protocol

Resolve the protocol in this order:

1. Check the active workspace via `ivy_workspace(action="get")`
2. Check `IVY_WORKSPACE_ROOT` environment variable
3. Scan the current working directory for `protocol-testing/` subdirectories

If still ambiguous, ask: "Which protocol should I review?"

### Step 3: Run triage preflight

Invoke `triage` as a sub-workflow to confirm MCP/LSP health before dispatching agents:

1. Set the active-workflow flag:
   - `workflow = "triage"`
   - `phase = "preflight"`
   - `invocation_depth` = current depth + 1
   - `caller = "review"`
2. Invoke: `Skill(skill="triage")`
3. Triage runs Phase 1 only (because `invocation_depth > 0`). Returns silently if healthy.
4. After triage returns, restore:
   - `workflow = "review"`
   - `phase = "triaged"`

### Situation Briefing — Review Type Confirmation

Load the `reflection-patterns` skill. Apply **Pattern C (Situation Briefing)**:

- **What happened:** "Detected review type: [Coverage / Quality / Both]. Protocol: [protocol]. Stack health: [passed / required intervention]."
- **What it means:** Explain what this review type will check and approximately how long it takes.
- **Options:** "Proceed with [detected type] review" / "Switch to [other type]" / "Run both coverage and quality"

### Step 4: Update state

Update phase to `"triaged"` via `update_workflow_phase()`.

---

## Phase 2 — Execute

Branch by the review type detected in Phase 1.

### Coverage Path

Dispatch the `traceability-agent` agent:

1. The agent extracts RFC requirements from existing manifests, or reads `build-state.yaml` for the target RFC(s).
2. The agent scans `.ivy` files for bracket-tag annotations (`# [rfcNNNN:X.Y]`).
3. The agent reports coverage by priority:
   - MUST requirements: covered/total
   - SHOULD requirements: covered/total
   - MAY requirements: covered/total
4. The agent lists gaps ordered by priority (uncovered MUST first).

### Quality Path

#### Multi-Perspective Exploration — Quality Analysis

Load the `reflection-patterns` skill. Apply **Pattern B (Multi-Perspective Exploration)** with 3 agents:

- **Exploration question:** "What are the quality issues in this protocol model?"
- **Agents (dispatch all 3 in parallel):**
  - **model-reviewer** (use existing agent definition): 6-category structural audit (structural, type safety, invariants, actions, initialization, organization)
  - **spec-analyst** (use existing agent definition): Verification readiness, include trace, layer coherence
  - **Adversarial Auditor** (Explore): Red-team the model — find edge cases the structured audits miss, question assumptions in the spec, identify states that could be reached but aren't tested

Synthesize findings from all 3 agents before presenting.

Dispatch `model-reviewer`, `spec-analyst`, and adversarial auditor agents IN PARALLEL (three Agent tool calls in one message):

**model-reviewer** runs a 6-category structural audit:

1. Structural correctness (headers, includes, circular deps)
2. Type safety (annotations, mismatches, enumerations)
3. Invariant completeness (ungrounded vars, missing invariants, strength)
4. Action well-formedness (preconditions, postconditions, guards)
5. Initialization (`after init` blocks, consistency with invariants)
6. Organization (naming, isolate boundaries, duplication)

**spec-analyst** checks:

1. Verification readiness (will `ivy_verify` pass?)
2. Include trace correctness (resolved paths, missing modules)
3. Layer coherence (are layers used consistently with the 14-layer template?)

Aggregate findings from both agents by severity: critical, important, suggestion.

### Both Paths

Run coverage and quality paths in parallel. Aggregate all findings into a unified report.

### Update state

Update phase to `"executed"` via `update_workflow_phase()`.

---

## Phase 3 — Findings

### Step 1: Present findings

Present findings with severity classification:

- **Critical:** Verification will fail, or the model is unsound. Must fix before committing.
- **Important:** Quality concern that a code reviewer would flag. Should fix.
- **Suggestion:** Improvement that doesn't affect correctness.

Load the `claim-discussion` knowledge skill for structured discussion of any contested findings.

### Gate checkpoint on critical issues

If critical issues were found: "These critical issues were found: [list]. Fix them now? Run verify on flagged files?"

Wait for explicit confirmation.

### Reflection Gate — Post-Findings Direction

Load the `reflection-patterns` skill. Apply **Pattern A (Reflection Gate)**:

- **Current state:** "[N] critical, [N] important, [N] suggestion findings across [coverage/quality/both] analysis."
- **Re-evaluate:** Do the findings suggest a different workflow is needed?
  - Many structural issues -> `build` workflow to fix the model architecture
  - Verification failures -> `verify` workflow to diagnose specific failures
  - Coverage gaps only -> stay in `review` to address gaps
- **Alternative workflows:** `build` (structural fixes), `verify` (targeted verification), stay in `review` (address findings inline)

### Step 2: Handle user response

**If the user wants fixes:**

Guide fixes inline using the relevant agent's recommendations. After applying fixes, re-run the analysis that found the issue to confirm resolution.

**If the user wants verification:**

**Depth limit:** If `invocation_depth >= 3`, do not invoke sub-workflows. Instead, return to the caller (decrement depth, restore caller's workflow) or return to navigate with a summary of what was attempted and what remains.

Dispatch to `verify` as a sub-workflow:

1. Set the active-workflow flag:
   - `workflow = "verify"`
   - `phase = "init"`
   - `invocation_depth` = current depth + 1
   - `caller = "review"`
2. Invoke: `Skill(skill="verify")`
3. After verify returns, restore:
   - `workflow = "review"`
   - `phase = "findings"`

**If the user accepts as-is:**

Proceed to completion.

---

## On Completion

- If `invocation_depth > 0`: Decrement depth. Restore `caller` as the active workflow in the active-workflow file. The caller resumes.
- If `invocation_depth == 0`: Clear the active-workflow flag via `clear_active_workflow()`. Navigate re-activates on the next user turn.

---

## Integration

- **Called by:** `navigate` (dispatch), `build` (quality gate — though build dispatches agents directly), `verify` (follow-up coverage), user directly ("review my model", "check coverage")
- **Calls:** `triage` (preflight), `traceability-agent` agent (coverage), `model-reviewer` agent (quality), `spec-analyst` agent (quality), `verify` workflow (optional follow-up)
- **Knowledge skills loaded:** `reflection-patterns` (SB Phase 1, MPE Phase 2, RG Phase 3), `claim-discussion` (Phase 3 for contested findings)
- **MCP tools used:** `ivy_workspace` (protocol detection)
- **State files:** `.panther-ivy/active-workflow`
