---
name: nct-review
description: Comprehensive Ivy specification review dispatching model-reviewer, spec-analyst, and traceability-agent
arguments:
  - name: aspects
    description: Which review aspects to run - "model", "verify", "coverage", or "all" (default). Comma-separated for multiple.
    required: false
  - name: target
    description: Path to a .ivy file or protocol directory to review (auto-detected from context if omitted)
    required: false
  - name: mode
    description: Dispatch mode - "auto" (default), "parallel", or "sequential". Auto uses sequential for single files, parallel for directories.
    required: false
---

Comprehensive Ivy specification review that dispatches multiple specialized agents and aggregates their findings.

## Instructions

### Step 1: Resolve Target

If no `target` argument is provided:
1. Check if there are recently modified `.ivy` files using `git diff --name-only` via Bash
2. If found, use those files as the target
3. If not, ask the user which file or directory to review

Determine target type:
- **Single file**: target ends in `.ivy` or is a single file path
- **Directory/protocol**: target is a directory path or protocol name (e.g., "quic")

If target is a protocol name (no path separators), resolve to `protocol-testing/{target}/`.

### Step 2: Resolve Aspects

Parse the `aspects` argument (default: "all"):
- `all` → dispatch model-reviewer + spec-analyst + traceability-agent
- `model` → dispatch model-reviewer only
- `verify` → dispatch spec-analyst only
- `coverage` → dispatch traceability-agent only
- Comma-separated (e.g., `model,coverage`) → dispatch the listed agents

### Step 3: Determine Dispatch Mode

Parse the `mode` argument (default: "auto"):
- `auto` → single `.ivy` file target uses sequential, directory target uses parallel
- `parallel` → always dispatch all agents simultaneously
- `sequential` → always dispatch agents in order: model-reviewer → spec-analyst → traceability-agent

### Step 4: Dispatch Agents

For each selected aspect, dispatch the corresponding agent using the Agent tool:

**model-reviewer** (aspect: `model`):
- Prompt: "Review the Ivy specification at `{target}` for correctness, completeness, and best practices. Focus on structural correctness, type safety, invariant quality, action correctness, initialization, and common anti-patterns. Report findings by severity (ERROR/WARNING/INFO)."

**spec-analyst** (aspect: `verify`):
- Prompt: "Analyze the Ivy specification at `{target}`. Run formal verification using ivy_verify, inspect model structure, and diagnose any issues found. Present results in structured PASS/FAIL format with suggested fixes for any failures."

**traceability-agent** (aspect: `coverage`):
- Prompt: "Review RFC traceability for the Ivy specification at `{target}`. Analyze the mapping between RFC requirements and Ivy assertions, identify coverage gaps, check tag consistency (orphaned tags, untagged assertions), and produce a prioritized coverage report."

**Dispatch rules:**
- **Sequential mode**: Launch model-reviewer first, wait for results, then spec-analyst, then traceability-agent. Pass findings from earlier agents as context to later ones.
- **Parallel mode**: Launch all selected agents simultaneously using multiple Agent tool calls in a single message.

### Step 5: Aggregate Results

After all agents complete, produce a unified review summary in this format:

```markdown
# Ivy Specification Review Summary

**Target:** {target}
**Aspects:** {aspects reviewed}
**Agents dispatched:** {list of agents}

## Critical Issues (X found)
{List all ERROR-level findings from model-reviewer and FAIL results from spec-analyst}
- [model-reviewer] {issue description} [{file}:{line}]
- [spec-analyst] {issue description} [{file}:{line}]

## Important Issues (X found)
{List all WARNING-level findings from model-reviewer and coverage gaps from traceability-agent}
- [model-reviewer] {issue description} [{file}:{line}]
- [traceability-agent] {coverage gap} [{rfcNNNN:X.Y}]

## Suggestions (X found)
{List all INFO-level findings and low-priority coverage items}
- [model-reviewer] {suggestion} [{file}:{line}]
- [traceability-agent] {suggestion} [{rfcNNNN:X.Y}]

## Strengths
{Highlight what's well-done across all review dimensions}

## Recommended Actions
1. Fix critical issues first
2. Address coverage gaps for uncovered MUST requirements
3. Resolve tag consistency issues
4. Re-run `/nct-review` after fixes to verify improvements
```

If only a subset of aspects was reviewed, omit sections that don't apply (e.g., no coverage section if traceability-agent wasn't dispatched).

### Step 5b: Interactive Discussion of Findings

After presenting the aggregated summary, engage the user interactively before moving to next steps. Reference the `interaction-patterns` and `claim-discussion` skills for format details.

**Critical Issues → Gate checkpoint (stop-and-discuss)**:
- Present each critical issue individually
- For verification failures, use the **Verification Claim Discussion** template from `claim-discussion`: state the violated property, show the evidence, ask "Is this property correct per the RFC?"
- Do NOT proceed to the next critical issue until the user has acknowledged or responded to the current one

**Important Issues → Collaborative checkpoint**:
- Present all important issues at once in a numbered list
- Ask: "Which of these would you like to prioritize? (numbers, 'all', or 'skip')"
- If the user selects specific issues, discuss those before continuing

**Suggestions → Inform-and-Continue**:
- State: "{N} suggestions identified (INFO-level). Proceeding to next steps — say 'show suggestions' to review them."
- Continue unless the user asks to see them

**Pre-Next-Steps Gate**:
- Before Step 6, ask: "Which critical/important issues should we address now? Or should I just list recommended next steps?"

### Step 6: Provide Next Steps

Based on the aggregate findings:
- If critical issues found → recommend fixing those first, then re-running `/nct-review`
- If only warnings/suggestions → recommend addressing them before committing
- If clean review → confirm the specification is ready for commit/verification
