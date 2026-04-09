---
name: review
description: "Quality and coverage auditing — detects review type from user intent and dispatches appropriate analysis agents. Activated for coverage checks, quality audits, and model reviews."
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

Dispatch `model-reviewer` and `spec-analyst` agents IN PARALLEL (two Agent tool calls in one message):

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

### Step 2: Handle user response

**If the user wants fixes:**

Guide fixes inline using the relevant agent's recommendations. After applying fixes, re-run the analysis that found the issue to confirm resolution.

**If the user wants verification:**

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
- **Knowledge skills loaded:** `claim-discussion` (Phase 3 for contested findings)
- **MCP tools used:** `ivy_workspace` (protocol detection)
- **State files:** `.panther-ivy/active-workflow`
