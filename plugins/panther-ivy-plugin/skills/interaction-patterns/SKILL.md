---
name: interaction-patterns
description: "Use when any agent needs to interact with the user during a workflow — defines checkpoint types, question formats, and follow-up strategies for consistent interaction across all agents."
---

# Interaction Patterns

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

Reusable interaction checkpoints for all Ivy plugin agents. Every agent references this skill for consistent user engagement.

## Checkpoint Types

### 1. Gate Checkpoint (Blocking)

**Purpose**: Agent MUST ask the user and wait for a response before proceeding. Used for decisions that change workflow direction.

**When to use**:
- Claim resolution (is this a spec bug or IUT non-compliance?)
- Scope selection (which files/protocols to analyze?)
- Priority decisions (which gaps to address first?)
- Ambiguous RFC interpretations

**Format**:
```
I found {finding}.

{context — 2-3 sentences explaining what this means}

Options:
(a) {option_a} — {brief consequence}
(b) {option_b} — {brief consequence}
(c) {option_c} — {brief consequence}

Which would you prefer?
```

**Rules**:
- Present 2-4 concrete options. Never present open-ended gates.
- Do NOT proceed until the user responds.
- If the user says "you decide" or "whatever you think", pick the most conservative option and state which you chose and why.
- If the user's response is ambiguous, ask a single clarifying follow-up.

---

### 2. Inform-and-Continue (Non-blocking)

**Purpose**: Agent informs the user of a finding and continues with a sensible default. User can interrupt to discuss.

**When to use**:
- Scope detection results (confirming detected context)
- Intermediate progress (halfway through analysis)
- Low-severity findings (INFO-level issues)
- Manifest generation results

**Format**:
```
I found {finding}. I'll proceed with {default_action} unless you want to discuss.
```

**Rules**:
- State the default action clearly.
- Continue immediately after informing — do not wait.
- If the user interrupts with a question, switch to Collaborative mode for that topic.

---

### 3. Collaborative Checkpoint (Discussion)

**Purpose**: Open-ended data presentation inviting joint analysis. No default path — agent and user explore together.

**When to use**:
- Presenting verification results summary
- Coverage gap analysis
- `assume` justification review
- Complex multi-finding summaries
- End-of-analysis discussion

**Format**:
```
Here's what I see:

{structured data — table, list, or summary}

{1-2 open questions inviting interpretation}
```

**Rules**:
- Present data first, then ask for interpretation.
- Ask at most 2 open questions.
- Wait for the user to engage before offering your own analysis.
- If the user asks you to proceed autonomously, switch to Inform-and-Continue for remaining items.

---

## Question Formats

### Single-Choice
```
Which {topic}?
(a) {option_a}
(b) {option_b}
(c) {option_c}
```
Use when options are mutually exclusive.

### Multi-Choice
```
Which of these should we address? (select any)
- [ ] {option_a}
- [ ] {option_b}
- [ ] {option_c}
```
Use for prioritization (e.g., which coverage gaps to fix).

### Confirmation
```
I'm about to {action}. Proceed? (y/n)
```
Use before irreversible actions (writing to files, generating manifests).

### Open-Ended
```
{context}. What's your interpretation?
```
Use sparingly — only in Collaborative checkpoints.

---

## One Question at a Time Rule

**CRITICAL**: Never combine multiple questions in a single message. Each interaction should have exactly ONE question or decision point.

Bad:
```
Should we fix the invariant? Also, which RFC section does this map to? And do you want me to check coverage?
```

Good:
```
Should we fix this invariant, or is the assertion intentionally relaxed?
```

If you need multiple answers, sequence them — ask the most important question first, then follow up after the response.

---

## Adaptive Follow-Up Rules

### When to Drill Deeper
- User expresses uncertainty ("I'm not sure", "maybe", "I think so")
- Finding has ERROR severity
- User asks "why?" or "how?"
- Counterexample trace is non-trivial (>3 steps)

### When to Move On
- User gives a confident answer
- Finding is INFO severity
- User says "skip", "next", "move on"
- Same topic has been discussed for >2 exchanges

### When to Revisit
- Later finding contradicts an earlier decision
- User explicitly asks to revisit ("wait, go back to...")
- Coverage analysis reveals a gap related to an earlier claim resolution

### Expertise Adaptation
- **Expert signals**: Uses Ivy/RFC terminology, gives terse answers, says "just do it"
  - Response: Fewer explanations, more options, use domain shorthand
- **Beginner signals**: Asks "what does X mean?", gives long uncertain answers
  - Response: More context per question, simpler options, explain Ivy concepts inline
- **Mixed signals**: Treat as expert but offer "want me to explain?" escape hatch

---

## Checkpoint Selection Guide

| Situation | Checkpoint Type |
|-----------|----------------|
| Verification failure with counterexample | Gate |
| Scope/file detection at start | Inform-and-Continue |
| Each ERROR finding | Gate |
| Each WARNING with `assume` | Collaborative |
| Coverage gap list | Gate (for prioritization) |
| RFC requirement interpretation | Gate |
| Intermediate progress update | Inform-and-Continue |
| Final summary presentation | Collaborative |
| Before writing to .ivy files | Confirmation (Gate) |
| Methodology detection | Collaborative |

## Integration
- **LOADED BY:** All agents (checkpoint types and question formats)
- **LOADED BY:** ivy-workflow-orchestrator (gate checkpoint patterns)
- **USED BY:** All commands with interactive checkpoints
