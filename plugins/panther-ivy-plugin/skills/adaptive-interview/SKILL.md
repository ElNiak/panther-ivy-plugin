---
name: adaptive-interview
description: "Use when the Navigator agent needs to interview the user to determine their goal and guide them through the appropriate Ivy testing workflow."
prerequisites: ["interaction-patterns"]
---

# Adaptive Interview

Defines the Navigator agent's interview logic for determining user goals and routing to the appropriate workflow or agent.

## Interview Phases

### Phase 1: Context Detection (Automatic — No Questions)

Gather context silently before asking anything:

1. **Workspace context**: Read the SessionStart hook output for detected Ivy workspace path and protocol.
2. **Recent changes**: Check `git diff --name-only HEAD~3..HEAD` for recently modified `.ivy` files. Note which protocol directory and layer they belong to.
3. **Conversation history**: Scan for domain terms the user has already used:
   - Ivy/formal terms → expert
   - General terms ("test", "check") → may be beginner
   - Specific RFC numbers → they know what they want
4. **Open files**: If the user mentioned a specific file, note it as the likely target.

**Output**: Internal context record (not shown to user):
```
workspace: {path}
protocol: {detected_protocol}
recent_files: [{file1}, {file2}]
expertise: {expert|intermediate|beginner}
likely_target: {file_or_none}
```

---

### Phase 2: Goal Identification (1 Adaptive Question)

**If context strongly suggests a goal** — confirm it (Inform-and-Continue):
```
I see you've been working on {context}. I'll help you {detected_goal} unless you had something else in mind.
```

**If context is ambiguous** — ask (Gate):
```
I see {context_summary}. What are you looking to do?

(a) Create or extend a protocol specification
(b) Add RFC requirements to an existing spec
(c) Debug a verification failure
(d) Review coverage or quality
(e) Something else — describe it
```

**If no context at all** — ask openly but with structure:
```
What would you like to work on?

(a) Build a new protocol specification from scratch
(b) Work on an existing spec (verify, extend, debug)
(c) Extract and map RFC requirements
(d) Review specification quality or coverage
(e) Learn about NCT/NACT/NSCT methodology
```

Map responses to goals:

| Response | Goal | Next Phase |
|----------|------|------------|
| Create/extend spec | `create` | Phase 3 (methodology) then Phase 4 (scoping) |
| Add requirements | `requirements` | Skip Phase 3, Phase 4 (target file) |
| Debug failure | `debug` | Skip Phase 3, Phase 4 (target file) |
| Review coverage/quality | `review` | Skip Phase 3, Phase 4 (scope) |
| Learn methodology | `learn` | Phase 3 (which methodology) |
| Something else | `custom` | Follow-up question |

---

### Phase 3: Methodology Selection (0-1 Questions)

**Skip if**: Goal is `debug`, `requirements`, or `review` (methodology is implied as NCT).

**Auto-detect if possible**:
- Files in `apt/` or mentions of "attack"/"security" → NACT
- Mentions of "Shadow NS", "simulation", "topology" → NSCT
- Everything else → NCT

**If ambiguous** (Gate):
```
Which testing approach fits your needs?

(a) NCT — Specification compliance testing (Ivy generates test traffic against an IUT)
(b) NACT — Security/attack testing (APT lifecycle, attacker entities)
(c) NSCT — Simulation-based testing (Shadow NS, scale, network conditions)
(d) Not sure — describe what you want to verify
```

---

### Phase 4: Target Scoping (1-2 Adaptive Questions)

Questions depend on the goal from Phase 2:

#### Goal: `create`
```
Which protocol are you specifying?

(a) QUIC (extend existing model)
(b) {other detected protocols from workspace}
(c) New protocol — what's it called?
```

Then:
```
Which layers should we start with? (The minimum viable set is 7 layers)

(a) Start with the minimum: Types, Frame, Packet, Connection, Entity, Behavior, Shim
(b) Full 14-layer scaffold
(c) Specific layers only — which ones?
```

#### Goal: `debug`
```
Which file has the verification failure?

(a) {recently_modified_file_1}
(b) {recently_modified_file_2}
(c) Other — specify the path
```

#### Goal: `requirements`
```
Which RFC are we extracting requirements from?

(a) RFC 9000 (QUIC Transport)
(b) RFC 9001 (QUIC TLS)
(c) Other — specify RFC number
```

#### Goal: `review`
```
What scope should I review?

(a) Single file: {likely_target}
(b) Entire protocol: {detected_protocol}
(c) Specific test endpoint: {suggest based on recent files}
(d) Full workspace
```

#### Goal: `learn`
No scoping needed — dispatch directly to methodology-guide agent.

---

### Phase 5: Dispatch (Automatic)

Based on collected context, route to the appropriate agent or workflow:

| Goal | Methodology | Dispatch Target |
|------|-------------|-----------------|
| `create` | NCT | Start `incremental-spec-dev` skill workflow |
| `create` | NACT | Dispatch to `methodology-guide` agent (NACT focus) |
| `create` | NSCT | Dispatch to `methodology-guide` agent (NSCT focus) |
| `debug` | any | Dispatch to `spec-analyst` agent with file path |
| `requirements` | any | Dispatch to `traceability-agent` with RFC info |
| `review` | any | Dispatch to `model-reviewer` agent with scope |
| `learn` | specific | Dispatch to `methodology-guide` agent |

**Dispatch message format**:
```
Based on our discussion, I'll {action_description}.

{Brief summary of context being passed to the target agent}
```

After dispatch, the Navigator remains available for follow-up routing. If the dispatched agent completes and the user wants to continue, the Navigator picks up for the next goal.

---

## Adaptive Behavior Rules

### Expertise Calibration

| Signal | Classification | Behavior |
|--------|---------------|----------|
| Uses Ivy syntax terms (`isolate`, `before`, `after init`) | Expert | Skip explanations, use technical shorthand |
| References specific RFC sections by number | Expert | Skip RFC explanation, go straight to mapping |
| Asks "what is X?" for Ivy concepts | Beginner | Add brief inline explanations |
| Uses general terms ("test file", "check") | Intermediate | Normal verbosity |
| Says "just do it" or "you decide" | Expert (or impatient) | Pick defaults, minimize questions |

### Question Reduction

- If Phase 1 context answers a question, skip it entirely.
- If the user's initial message already specifies a goal, skip Phase 2.
- If the user mentions a methodology, skip Phase 3.
- If the user names a file, skip Phase 4 scoping.
- **Maximum questions before dispatch: 3** (across all phases).

### Context-Aware Suggestions

When presenting options, highlight the most likely choice based on context:
```
What are you looking to do?

(a) Debug the verification failure in quic_connection.ivy  <-- likely, based on your recent changes
(b) Review coverage for the QUIC client test endpoint
(c) Something else
```

---

## Multi-Step Workflow Support

For goals that span multiple steps (e.g., `create` involves scaffolding, then writing, then verifying), the Navigator provides transition checkpoints:

```
Step {N} complete: {summary}.

Next step: {description}.
Ready to continue, or would you like to adjust the approach?
```

Use Inform-and-Continue for routine transitions. Use Gate for transitions that change direction.

## Integration
- **LOADED BY:** navigator agent (interview workflow)
- **CHAINS TO:** ivy-workflow-orchestrator (when user goal is spec creation/modification -> deep mode)
- **CHAINS TO:** Fast-mode commands (when user goal is informational/diagnostic)
- **PREREQUISITES:** interaction-patterns
