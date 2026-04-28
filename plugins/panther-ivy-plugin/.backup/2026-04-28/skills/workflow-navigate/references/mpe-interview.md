# Navigate — Multi-Perspective Exploration for ambiguous cold-start goals

Cold-path procedure extracted from `navigate/SKILL.md` so the hub skill
stays lean. Load this file when Phase 2 Branch C (Cold Start) is active AND
the user's goal is ambiguous.

## When to run MPE

MPE runs only on cold-start, and only on the axes that are actually
ambiguous. The agent count scales from 0 to 3 based on how much of the
user's intent is already clear from their opening message. This matches
Anthropic's Opus 4.7 guidance — fan out subagents for genuinely parallel
work, direct-reason when a single dispatch would suffice.

## Axis classification

Inspect the user's opening message and classify each axis as **clear** or
**ambiguous**:

<axes>

<axis name="protocol_axis">
- **clear** — a protocol name appears (quic, bgp, coap, minip, apt,
  apt_quic, etc.) OR the active workspace already pins a protocol.
- **ambiguous** — no protocol named and no active workspace.
</axis>

<axis name="goal_axis">
- **clear** — a workflow verb appears:
  `build | scaffold | create | extend | model` → build;
  `verify | check | test | debug | handshake | counterexample` → verify;
  `review | audit | coverage | quality | traceability | gap` → review;
  `broken | error | tools | MCP | LSP | server down | timeout` → triage.
- **ambiguous** — no verb matches, or two or more verbs match with equal
  weight.
</axis>

<axis name="methodology_axis">
- **clear** — NCT, NACT, or NSCT keyword appears in the message, OR the
  inferred goal uniquely implies one (`attack / adversary / security` →
  NACT; `simulation / topology / timer / shadow` → NSCT; otherwise NCT).
- **ambiguous** — no keyword and no unique implication.
</axis>

</axes>

Let `N = number of ambiguous axes, capped at 3`.

## Dispatch table

| N | Action |
|---|--------|
| 0 | Skip MPE entirely. Proceed to the interview with a one-question confirmation of the inferred routing. |
| 1 | Dispatch one `Explore` subagent targeting the ambiguous axis (see templates below). Synthesize, then interview. |
| 2 | Dispatch two `Explore` subagents in a single response (parallel tool calls), one per ambiguous axis. Synthesize, then interview. |
| 3 | Dispatch three `Explore` subagents in a single response (parallel tool calls), one per axis. Synthesize, then interview. |

Each `Explore` returns a one-paragraph recommendation under 100 words.

## Per-axis dispatch templates

Substitute `<user_message>` and `<protocol_hint>` from the opening message.
Dispatch only the axes the classifier flagged as ambiguous.

<dispatch target="Explore" via="agent" role="Methodology Expert"
          when="methodology_axis == ambiguous"
          question="Given the user's message '<user_message>' and protocol hint '<protocol_hint>', which methodology fits best: NCT (RFC compliance), NACT (attacker-model security), or NSCT (simulation and timing)? Report the choice and a one-sentence rationale under 100 words."/>

<dispatch target="Explore" via="agent" role="Workflow Expert"
          when="goal_axis == ambiguous"
          question="Given the user's message '<user_message>', which PANTHER workflow best serves their immediate need: build (author new model), verify (run tests and diagnose), review (coverage and quality audit), or triage (tool health). Report the workflow and a one-sentence rationale under 100 words."/>

<dispatch target="Explore" via="agent" role="Protocol Expert"
          when="protocol_axis == ambiguous"
          question="Given the user's message '<user_message>', which existing protocol directory under protocol-testing/ most closely matches their intent, or should they start a new one? Report the protocol name (or 'new') and a one-sentence rationale under 100 words."/>

Present the synthesized recommendation to the user, then proceed with the
interview questions — asking only about axes that remain unresolved after
the synthesis.

## Interview questions

Ask one question at a time. 1–3 focused questions total.

<instructions>

1. **What protocol?** "Which protocol are you working with?" (Skip if the
   workspace is already set or there's only one protocol directory.)
2. **What's your goal?** "What would you like to do?" Offer concise options:
   - Build a new protocol model
   - Continue or extend an existing model
   - Verify or debug a specification
   - Review coverage or quality
   - Learn about the methodology
3. **Which methodology?** "Which testing approach?" NCT (compliance), NACT
   (security), or NSCT (simulation). Skip if implied by the goal or if the
   user seems unfamiliar with the options — default to NCT.

</instructions>

Dispatch based on answers (see the Routing Table in `navigate/SKILL.md`).

<integration
  called-from="navigate/SKILL.md Phase 2 Branch C (Cold Start)"
  loads-skill="reflection-patterns (Pattern B)"
  agent-tier="Sonnet 90 s (MPE Explore agents, per .claude/rules/agent-dispatch.md)"/>
