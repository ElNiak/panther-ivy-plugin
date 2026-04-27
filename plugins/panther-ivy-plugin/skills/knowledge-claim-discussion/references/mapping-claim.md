# RFC Mapping Claim Discussion Template

**Trigger**: After `ivy_extract_requirements` or during traceability analysis when mapping RFC text to Ivy constructs.

---

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

<decision_tree>
The calling skill emits each `Question N` block below as an `AskUserQuestion` call; the prose inside code blocks is the template the skill substitutes into AskUserQuestion options, not text for Claude to paste into the conversation.

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
</decision_tree>

### Resolution Actions

| Resolution | Action |
|------------|--------|
| Add monitor | Write before/after clause + bracket tag |
| Mark N/A | Add to manifest as `testable: false` with reason |
| Adjust mapping | Edit proposed assertion per user guidance |
| Defer | Add to manifest without Ivy assertion |
