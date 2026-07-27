# Coverage Gap Claim Discussion Template

**Trigger**: After `ivy_coverage(mode="gaps")` returns uncovered requirements, or after traceability analysis reveals gaps.

---

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

<decision_tree>
The calling skill emits each `Question N` block below as an `AskUserQuestion` call; the prose inside code blocks is the template the skill substitutes into AskUserQuestion options, not text for Claude to paste into the conversation.

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
</decision_tree>

### Resolution Actions

| Resolution | Action |
|------------|--------|
| Prioritized list | Create skeleton monitors in priority order |
| Mark N/A | Update manifest with `testable: false` |
| Create monitors | Write before/after clauses with bracket tags |
| Defer | Record as known gap with rationale |
