---
name: claim-discussion
description: "Use when discussing verification claims, RFC requirement interpretations, or coverage gap priorities with the user. Provides structured decision trees for each claim type."
prerequisites: ["interaction-patterns", "counterexample-guide"]
---

# Claim Discussion

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

Structured discussion templates for resolving verification claims, RFC mapping decisions, and coverage gap priorities. Each template is a decision tree that guides agent-user interaction to a concrete resolution.

## A. Verification Claim Discussion

**Trigger**: After `ivy_verify` failure with counterexample, or after model-reviewer finds an ERROR.

### Opening

Present the counterexample trace summary:

```
ivy_verify FAILED on {file}:{isolate}

Violated property: {invariant or require statement}
Trace summary: {N}-step counterexample
  Step 1: {action}({params}) — {state change}
  Step 2: {action}({params}) — {state change}
  ...
  Final: {violated assertion} at line {N}

The assertion `{code}` does not hold after this sequence.
```

Use the `counterexample-guide` skill for detailed trace interpretation.

### Decision Tree

**Question 1** (Gate): "Is the violated assertion correct per the RFC?"

#### Branch: Yes — IUT Non-Compliance
```
This looks like a genuine IUT non-compliance.

The RFC says: "{rfc_text}" (RFC {N}, Section {X.Y})

Options:
(a) File as a test finding (the IUT violates the spec)
(b) Mark as known deviation — the IUT intentionally diverges
(c) Let me re-examine — I want to see the full RFC context
```

If (a): Add inline resolution comment and record in test findings.
If (b): Add `# KNOWN_DEVIATION: {reason}` comment.
If (c): Fetch/read the relevant RFC section, then re-ask Question 1.

#### Branch: No — Specification Issue
```
The assertion may be incorrect. What's wrong?

Options:
(a) Assertion is too strong — the RFC allows more flexibility
(b) Missing guard — a `before` clause should prevent this state
(c) Initialization issue — `after init` doesn't set the right default
(d) Let me see the RFC text to decide
```

If (a): Relax the assertion. Propose concrete fix and confirm.
If (b): Propose a `before` clause guard. Show the code and confirm.
If (c): Propose `after init` fix. Show the code and confirm.
If (d): Fetch/read RFC section, then re-present options.

#### Branch: Unsure
```
Let me show you the relevant RFC text so we can decide together.

RFC {N}, Section {X.Y}:
"{rfc_text}"

Given this text, does the assertion `{code}` correctly capture the requirement?
```

Then return to the Yes/No branches.

### Question 2 (Gate, if applicable): "Could this be a test generation issue?"

Ask this if the counterexample involves a `_generating` path:
```
The counterexample occurs during test traffic generation (inside a `_generating` guard).

Options:
(a) Add a generation constraint — restrict what the test mirror generates
(b) The `before` clause guard is missing — add a `require` in the `before` block
(c) This is a real spec issue, not a generation problem
```

### Resolution Actions

After reaching a decision, execute ONE of:

| Resolution | Action | Inline Comment |
|------------|--------|----------------|
| Spec fix | Edit the .ivy file with the agreed fix | `# RESOLVED({date}): {description}` |
| IUT finding | No spec change; record finding | `# IUT_FINDING({date}): {description}` |
| Generation guard | Add `require` in `before` block | `# GUARD_ADDED({date}): {description}` |
| Deferred | No change now; create follow-up | `# DEFERRED({date}): {reason}` |

---

## B. RFC Mapping Claim Discussion

**Trigger**: After `ivy_extract_requirements` or during traceability analysis when mapping RFC text to Ivy constructs.

### Opening

Present the RFC requirement:

```
RFC {N}, Section {X.Y}:
"{requirement_text}"

Keyword: {MUST|SHOULD|MAY} (RFC 2119)
Layer: {detected_layer}
Testable: {yes|no|partial} — {reason}
```

### Decision Tree

**Question 1** (Gate): "Does this mapping match your understanding?"
```
I'd map this to a {before|after} monitor on `{action_name}` in `{layer_file}`.

The Ivy assertion would be:
```ivy
{proposed_code}  # [rfc{N}:{X.Y}]
```

Does this capture the RFC intent?

Options:
(a) Yes — add this monitor with the bracket tag
(b) Close, but needs adjustment — {describe what to change}
(c) Wrong action/layer — this should be on {different_action}
(d) Not testable from the wire — mark as not-applicable
```

**Question 2** (Gate, for SHOULD/MAY only): "How strict should the assertion be?"
```
This is a {SHOULD|MAY} requirement. Options:

(a) Hard `require` — treat as mandatory for this IUT
(b) Monitored advisory — log when violated but don't fail the test
(c) Skip — not relevant for our testing goals
```

### Resolution Actions

| Resolution | Action |
|------------|--------|
| Add monitor | Write before/after clause + bracket tag |
| Mark N/A | Add to manifest as `testable: false` with reason |
| Adjust mapping | Edit proposed assertion per user guidance |
| Defer | Add to manifest without Ivy assertion |

---

## C. Coverage Gap Claim Discussion

**Trigger**: After `ivy_coverage(mode="gaps")` returns uncovered requirements, or after traceability analysis reveals gaps.

### Opening

Present gap summary:

```
Coverage Gap Analysis for {scope}

| Level | Covered | Total | Coverage |
|-------|---------|-------|----------|
| MUST  | {n}     | {N}   | {pct}%   |
| SHOULD| {n}     | {N}   | {pct}%   |
| MAY   | {n}     | {N}   | {pct}%   |

Highest-impact uncovered MUST requirements:
1. [rfc{N}:{X.Y}] "{text}" — Layer: {layer}
2. [rfc{N}:{X.Y}] "{text}" — Layer: {layer}
3. [rfc{N}:{X.Y}] "{text}" — Layer: {layer}
```

### Decision Tree

**Question 1** (Gate): "Which gaps should we prioritize?"
```
Which of these uncovered MUST requirements should we address?

- [ ] [rfc{N}:{X.Y}] "{text}" — estimated effort: {Low|Medium|High}
- [ ] [rfc{N}:{X.Y}] "{text}" — estimated effort: {Low|Medium|High}
- [ ] [rfc{N}:{X.Y}] "{text}" — estimated effort: {Low|Medium|High}

Or: (a) address all, (b) only Low-effort ones, (c) let me pick
```

**Question 2** (Gate, per selected requirement): "Where should the monitor go?"
```
For [rfc{N}:{X.Y}] "{text}":

Options:
(a) {before|after} monitor in {behavior_file} — {reason}
(b) {before|after} monitor in {stack_file} — {reason}
(c) New test variant in {test_dir} — {reason}
(d) Not applicable to this IUT — mark as N/A
```

**Question 3** (Collaborative): "Any requirements that aren't applicable?"
```
Are any of these requirements not applicable to your IUT or testing scenario?

{list of remaining uncovered requirements}

Mark any that should be excluded from coverage targets.
```

### Resolution Actions

| Resolution | Action |
|------------|--------|
| Prioritized list | Create skeleton monitors in priority order |
| Mark N/A | Update manifest with `testable: false` |
| Create monitors | Write before/after clauses with bracket tags |
| Defer | Record as known gap with rationale |

---

## Persistence — Inline Resolution Comments

All claim discussion outcomes are recorded as inline comments in `.ivy` files using this format:

```ivy
require conn_state = open;  # [rfc9000:4.1] RESOLVED(2026-03-18): Confirmed spec-correct per user
```

### Comment Prefixes

| Prefix | Meaning |
|--------|---------|
| `RESOLVED({date})` | Claim discussed and confirmed correct |
| `IUT_FINDING({date})` | IUT non-compliance identified |
| `GUARD_ADDED({date})` | Generation guard added per discussion |
| `DEFERRED({date})` | Decision postponed with reason |
| `KNOWN_DEVIATION({date})` | IUT intentionally diverges from spec |
| `N/A({date})` | Requirement not applicable with reason |

### Rules
- Always include the date in ISO format (YYYY-MM-DD)
- Keep comments concise (one line)
- Place on the same line as the assertion when possible
- For multi-line context, use a block comment above the assertion
- Never remove existing resolution comments — append if revisiting

## Integration
- **USED BY:** spec-analyst/model-reviewer agents (typically during orchestrator Phase 4)
- **USED BY:** /nct-check command -- for interactive claim discussion after verification
- **PREREQUISITES:** interaction-patterns, counterexample-guide
