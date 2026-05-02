---
paths: ["**/*.ivy", "**/*.spec", "**/skills/*/SKILL.md"]
---

<purpose>
Four canonical guidelines cited by the `scaffold`, `refine`, `experiment`, and `review` skills.
The text below is the canonical guidance; the workflow skills reference it
rather than duplicating the wording.

Skills MUST NOT re-cite iron-law text in their `SKILL.md` bodies — the rule
auto-loads on every skill entry via the `**/skills/*/SKILL.md` glob, so the
canonical wording, branch conditions, and worked examples below are always
in context. The per-workflow binding table at the top of this rule lists
which iron laws bind which workflow; consult it instead of restating in
SKILL.md.
</purpose>

<context>
The orchestrator's `skills/ivy/SKILL.md` body inlines a short iron-law
primer for main-thread visibility on every dispatch decision. This rule
auto-loads the full `<iron-law>` block detail on `.ivy`/`.spec` edits via
the `paths:` glob. Both surfaces stay in sync via this rule being the
canonical source — the primer is a summary derived from the rule body.
Edits here propagate to the orchestrator on the next refactor pass.

The advisory surface is the project-scoped `PreToolUse` hook at
`hooks/scripts/block-direct-ivy.py` (registered in `hooks/hooks.json` for
the `Bash` matcher). It surfaces an `[ivy-block] direct CLI call detected`
status line plus an MCP-tool suggestion table when `ivyc`, `ivy_check`,
`ivy_show`, or `ivy_to_cpp` is invoked from Bash, and **always exits 0**.
It is informational only — the actual enforcement of `NO_FIX_WITHOUT_VERIFY`
relies on workflow self-discipline (cite a fresh `ivy_verify` /
`ivy_compile` result before proposing a fix). See `ivy-toolkit/SKILL.md`
Enforcement section.

These guidelines are suspended during plan authoring (when the `navigate`
skill detects plan mode). The G0 plan-gate enforces conformance when a plan
is approved and the workflow re-activates at Phase 1.5.
</context>

## Iron Laws (scaffold, refine, experiment, review workflows)

| Law | Workflow | Enforcement site |
|---|---|---|
| NO_FIX_WITHOUT_VERIFY | refine | workflow self-discipline + hooks/scripts/block-direct-ivy.py (advisory hint) |
| NO_LAYER_WITHOUT_SCAFFOLD | scaffold | ivy_diagnostics(mode="structural") call before new-layer writes |
| NO_QUALITY_WITHOUT_COVERAGE | review | ivy_coverage / ivy_quality citation at verdict time |
| STALENESS RULE | scaffold, refine, experiment, review | ivy_analysis(mode="includes") closure + tool timestamp |

<iron-law name="NO_FIX_WITHOUT_VERIFY" workflow="refine" enforcement="hooks/scripts/block-direct-ivy.py (advisory) + workflow self-discipline">

  <instructions>
  Before proposing a *concrete code-edit fix* (an Edit/Write tool call, or a
  diff offered to the user) for a verification failure, ground it in the
  relevant verification check from the current turn: `ivy_verify` for
  end-of-phase verdicts, or `ivy_compile` + IUT during the dev iteration
  loop (per `feedback_ivy_verify_slow.md` — formal verification is deferred
  to end-of-phase + background; compile + IUT carries iteration). Cite which
  check ran when proposing the fix.
  </instructions>

  <branch condition="allowed without prior verify" name="upstream-activities">
  These are upstream activities that produce the fix proposal, not the
  proposal itself:

  - The `ivy-debugging-methodology` pre-fix research workflow.
  - Hypothesis generation, root-cause analysis, naming candidate edit sites.
  - Reading code, running `ivy_diagnostics`, looking up symbols via LSP.
  - Comment-only edits and RFC bracket-tag annotations that don't change
    `before`/`after`/`invariant`/`require`/`ensure` logic.
  </branch>

</iron-law>

<iron-law name="NO_LAYER_WITHOUT_SCAFFOLD" workflow="scaffold" enforcement="ivy_diagnostics(mode=structural) precondition in scaffold Phase 3">

  <instructions>
  Before writing a *net-new* layer file (e.g., creating `quic_8.ivy` when
  `quic_7.ivy` is the latest layer in `{prot}_stack/`), ground the decision
  in `ivy_diagnostics(mode="structural")` returning no
  <severity class="finding" value="ERROR"/>-severity diagnostics for the
  prior layer. Reason: stacking a new layer on top of a structurally broken
  predecessor compounds the breakage and makes the structural diagnostics
  ambiguous about which layer to fix.
  </instructions>

  <branch condition="out of scope — no structural pass required" name="non-layer-writes">
  Patches and auxiliary files are free to author without a structural pass:

  - Patches to existing layer files (bug fixes, refactors, additions to a
    layer that already compiles structurally).
  - Authoring entity, shim, test, or utility files outside `{prot}_stack/`.
  - Sketching a new layer in a draft file outside the workspace's discovery
    path.
  </branch>

  <context>
  "No <severity class="finding" value="ERROR"/>-severity" means the
  diagnostics array contains no entry with `severity == "error"`.
  <severity class="finding" value="WARNING"/> and
  <severity class="finding" value="INFO"/> entries do not block.
  </context>

</iron-law>

<iron-law name="NO_QUALITY_WITHOUT_COVERAGE" workflow="review" enforcement="ivy_coverage / ivy_quality citation at verdict emission">

  <instructions>
  Before stating a *formal coverage or quality verdict* — claims like "this
  model is X% complete", "this isolate has insufficient guards", "the
  requirement set is fully covered", or any pass/fail judgment on a coverage
  or quality dimension — cite `ivy_coverage` and/or `ivy_quality` output
  from the current turn inline. Reason: coverage verdicts that are not
  grounded in a fresh tool result drift quickly as the spec evolves; an
  unscoped claim becomes an opinion that consumers cannot verify or audit.
  </instructions>

  <branch condition="not a quality verdict — judgment space, no tool citation required" name="qualitative-feedback">
  The following are judgment-space, not quality verdicts:

  - Style and naming feedback ("consider renaming this action").
  - Readability and structural clarity comments.
  - RFC-alignment phrasing suggestions or comment-quality observations.
  - Discussions of design alternatives where no formal pass/fail is asserted.

  If the assessment is qualitative ("looks reasonable") it is not a quality
  verdict. If it asserts a measured property of the model, cite the tool
  output that supports it.
  </branch>

</iron-law>

<iron-law name="STALENESS_RULE" workflow="scaffold, refine, experiment, review" enforcement="ivy_analysis(mode=includes) closure + tool result timestamp">

  <instructions>
  A tool result for file `F` is *stale* if `F` itself or any file in `F`'s
  transitive include closure was modified after the tool result's recorded
  timestamp. The closure is the set returned by
  `ivy_analysis(mode="includes", relative_path=F)`.

  - Edits to workspace files outside `F`'s include closure do not
    invalidate the result.
  - The recorded timestamp is whatever the tool returns (commonly
    `started_at` for `ivy_verify`; if absent, treat the result's age as
    zero only for the current turn).
  - A workflow dispatched via `pending_dispatch` is a new causal frame;
    prior tool results in the emitting workflow remain valid unless the
    dispatched workflow edits files in the emitting workflow's include
    closure.
  - Stale results don't count as evidence — re-run the relevant tool
    before claiming <severity class="tool-outcome" value="PASS"/>,
    transitioning phases, or proposing a concrete patch.
  - If `ivy_analysis(mode="includes")` is unavailable in the current
    session, fall back to workspace-wide invalidation and note the
    conservative scope when citing the result.
  </instructions>

  <context>
  Operational citations — where each owning workflow applies the staleness
  check:

  - **verify**: Phase 2 runs `ivy_diagnostics` on recently modified files
    before `ivy_verify`; Phase 4 re-runs `ivy_verify` if any file in the
    target's include closure changed since the prior PASS.
  - **scaffold**: Phase 3 re-runs `ivy_diagnostics(mode="structural")` on a
    predecessor layer if the closure includes a file edited since the
    prior structural pass — the NO_LAYER_WITHOUT_SCAFFOLD gate consumes
    a fresh result, not a cached one.
  - **review**: Phase 2 re-runs `ivy_coverage` / `ivy_quality` before
    emitting a verdict when the spec tree under review has been edited
    since the last coverage snapshot.
  </context>

</iron-law>

<integration
  cited-by="skills/scaffold-ops, skills/refine-ops, skills/experiment-ops, skills/review-ops"
  enforcement-hook="hooks/scripts/block-direct-ivy.py (advisory hint)"
  suspended-during="plan mode (navigate Phase 0)"
  re-checked-at="G0 plan-gate on plan approval (navigate Phase 1.5)"/>

## Worked application

Each iron law applied to a real artifact, so the abstract `<instructions>` blocks above have a concrete shape readers can recognise on sight. The canonical wording is unchanged; the examples below are illustrative.

### NO_FIX_WITHOUT_VERIFY in flight

```text
Turn N    : ivy_verify(quic_server_test_handshake.ivy)
            → {"status":"FAIL","counterexample":{...},"started_at":"…14:02Z"}
Turn N+1  : ivy-refiner-agent proposes  + require initial_received(scid);
            (allowed — upstream activity, not a claim)
Turn N+2  : Edit applied. Iron law BINDS — no resolution claim yet.
Turn N+3  : ivy_verify rerun → {"status":"OK","started_at":"…14:08Z"}
            → "verification passed" claim is now licensed.
```

Direct CLI alternative `ivy_check quic_server_test_handshake.ivy` is warned by `hooks/scripts/block-direct-ivy.py` (PreToolUse, exit 0 advisory hint with MCP-tool suggestion table).

### NO_LAYER_WITHOUT_SCAFFOLD in flight

```text
Author wants: Write quic_8.ivy (a new layer on top of quic_7.ivy).
Iron law:     Run ivy_diagnostics(mode=structural) on quic_7.ivy first.
              → SOUND. Write quic_8.ivy is licensed.
              → ERROR diagnostics. Fix quic_7.ivy or DEFERRED-promote
                each finding before authoring quic_8.ivy.
```

Patches to existing layer files (bug fixes, refactors) are out of scope — the rule binds new-layer authoring only.

### NO_QUALITY_WITHOUT_COVERAGE in flight

```text
Reviewer wants to claim: "Coverage looks good for RFC 9000 §17.2".
Iron law:                cite a fresh ivy_coverage / ivy_quality output.
            → ivy_coverage(test_file=…) returns {gaps:[], covered:42/42}.
            → "Coverage SOUND for §17.2" claim now licensed; cite the
              tool result by timestamp.
```

Personal heuristic ("looks fine") does NOT discharge the rule.

### STALENESS_RULE in flight

```text
Turn N    : ivy_verify returns OK at 09:14:02Z.
Turn N+5  : Edit on quic_packet.ivy (in the include closure).
Turn N+6  : Reviewer wants to cite "verify is SOUND".
Iron law  : the OK from Turn N is stale — its include closure changed.
            Re-run ivy_verify before citing.
```

`ivy_analysis(mode="includes")` returns the closure that defines whether a result is stale. Workspace-wide invalidation is the conservative fallback.
