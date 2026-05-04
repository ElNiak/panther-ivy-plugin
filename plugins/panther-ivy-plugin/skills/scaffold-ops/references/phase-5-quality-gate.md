# Build — Phase 5 Quality Gate Detail

Phase 5 quality-gate procedure plus the related per-file G2/G3 gate semantics that feed the quality assessment. Read when running a quality-gate cycle.

## G2 / G3 Gates Fire Per-File (Phase 3 prerequisite)

After each `Write`/`Edit` on a `.ivy` file, the builder agent dispatches critics inline (per `scaffold-ops/SKILL.md` Phase 3 G2/G3 hard-gate); the PostToolUse hooks `posttooluse/gates/g2-modeling.py` and `posttooluse/gates/g3-testspec.py` are a backstop. Critic prompts come from the verbatim G2/G3 catalog templates kept under `skills/ivy/references/critic_prompts/`:

- `*.ivy` (non-test): G2 modeling critics (catalog slice `#200-249` + `#250-299` + NSCT `#260-289`).
- `*_test_*.ivy`: G3 test-spec critics (catalog slice `#200-208` + `#256-259` + `#300-399`).

On `VERDICT_UNSOUND`, the orchestrator writes `[GAP: #NN <reason>]` markers inline at the cited locations. Before starting the next layer, resolve every `[GAP:]` marker open across the current Phase 3 lifecycle — not just markers from the most recent write. Each marker is either fixed in place or deliberately promoted to `// DEFERRED YYYY-MM-DD: …` per `.claude/rules/gap-markers.md`. On `VERDICT_ABSTAIN`, the verdict lands silently in the workflow journal; read it at the next Reflection Gate.

## Phase 5 — Quality Gate Detail

### Step 1: Dispatch review agents in parallel

Dispatch both agents in a single message using two `Agent` tool calls:

<dispatch target="ivy-reviewer-agent" via="agent" phase="5"
          reason="Phase 5 quality audit — structural correctness, type safety, invariant completeness, action well-formedness, initialization, organization"/>

<dispatch target="ivy-reviewer-agent" via="agent" phase="5"
          reason="Phase 5 coverage audit — RFC coverage check against the blueprint's target RFC(s)"/>

Sequencing: the `Agent(...)` calls go in a single message so the two agents run in parallel.

### Step 2: Aggregate findings

Collect findings from both agents. Classify by severity per `.claude/rules/ivy-formatting.md` Severity Systems ("Finding severity"):
<severity class="finding" value="ERROR"/> /
<severity class="finding" value="WARNING"/> /
<severity class="finding" value="INFO"/>.

### Gate checkpoint on ERROR findings

<checkpoint type="gate" id="phase-5-error-findings">
If any <severity class="finding" value="ERROR"/> findings are produced, present them to the user: "These ERRORs were found: [list]. Fix them now? Or accept and move on?" Wait for explicit confirmation.
</checkpoint>

### Step 3: Handle fixes

If the user wants fixes:

- For structural issues (type safety, invariants, initialization): loop back to Phase 3 to fix the affected layers.
- For verification issues (failed properties, counterexamples): loop back to Phase 4 to re-verify.
- For coverage gaps: add missing monitors inline, then re-run the traceability check.

### Situation Briefing — Quality Gate Results

Apply the **Situation Briefing** pattern (a structured pre-action context dump):

- **What happened:** Summarize the quality gate results — how many findings by severity (critical/important/suggestion), which agents found what, overall model health.
- **What it means:** Are ERROR-severity findings blocking? Is coverage sufficient for the target methodology?
- **Options:**
  - "Fix ERROR findings now" (if any exist)
  - "Proceed to wrap-up — accept current quality level"
  - "Run full verification before wrapping up"
  - "Review coverage gaps in detail"

### Step 4: Update state

Update phase to `"quality-passed"` via `ivy_workflow_state(action="set", workflow="scaffold", phase="quality-passed", protocol="<protocol>")`.

### Knowledge Gate: Post-Quality-Gate

**KNOWLEDGE GATE (KG)**: Pause for the G6 knowledge-capture vote — the orchestrator dispatches `g-knowledge-critic` ×3 in parallel (asymmetric vote) on whether session learnings are worth persisting (rules, references, feedback memory).

- Reflect on architecture decisions solidified during quality review.
- Capture ivy-reviewer-agent findings worth remembering.
- Save session log (observability events + digest).
- If candidates found, classify and present for user confirmation.
- Resume workflow after the vote completes.
