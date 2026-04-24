# Verification Claim Discussion Template

**Trigger**: After `ivy_verify` failure with counterexample, or after model-reviewer finds an ERROR.

---

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

<decision_tree>
The calling skill emits each `Question N` block below as an `AskUserQuestion` call; the prose inside code blocks is the template the skill substitutes into AskUserQuestion options, not text for Claude to paste into the conversation.

**Question 1** (Gate): "Is the violated assertion correct per the RFC?"

<branch name="Yes — IUT Non-Compliance">
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
</branch>

<branch name="No — Specification Issue">
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
</branch>

<branch name="Unsure">
#### Branch: Unsure
```
Let me show you the relevant RFC text so we can decide together.

RFC {N}, Section {X.Y}:
"{rfc_text}"

Given this text, does the assertion `{code}` correctly capture the requirement?
```

Then return to the Yes/No branches.
</branch>

### Question 2 (Gate, if applicable): "Could this be a test generation issue?"

Ask this if the counterexample involves a `_generating` path:
```
The counterexample occurs during test traffic generation (inside a `_generating` guard).

Options:
(a) Add a generation constraint — restrict what the test mirror generates
(b) The `before` clause guard is missing — add a `require` in the `before` block
(c) This is a real spec issue, not a generation problem
```
</decision_tree>

### Resolution Actions

After reaching a decision, execute ONE of:

| Resolution | Action | Inline Comment |
|------------|--------|----------------|
| Spec fix | Edit the .ivy file with the agreed fix | `# RESOLVED({date}): {description}` |
| IUT finding | No spec change; record finding | `# IUT_FINDING({date}): {description}` |
| Generation guard | Add `require` in `before` block | `# GUARD_ADDED({date}): {description}` |
| Deferred | No change now; create follow-up | `# DEFERRED({date}): {reason}` |
