---
paths: ["**/*.ivy", "**/*.spec"]
---

<purpose>
Four canonical guidelines cited by the `build`, `verify`, and `review` skills.
The text below is the canonical guidance; the workflow skills reference it
rather than duplicating the wording.
</purpose>

<context>
The deterministic enforcement layer is the project-scoped `PreToolUse` hook
at `hooks/scripts/block-direct-ivy.sh` (registered in `hooks/hooks.json` for
the `Bash` matcher), which warns (exit 0) about direct CLI invocations of
`ivyc`, `ivy_check`, `ivy_show`, and `ivy_to_cpp` and suggests their MCP
equivalents — see `ivy-toolkit/SKILL.md` Enforcement section.

These guidelines are suspended during plan authoring (when the `navigate`
skill detects plan mode). The G0 plan-gate enforces conformance when a plan
is approved and the workflow re-activates at Phase 1.5.
</context>

## Iron Laws (build, verify, review workflows)

| Law | Workflow | Enforcement site |
|---|---|---|
| NO_FIX_WITHOUT_VERIFY | verify | hooks/scripts/block-direct-ivy.sh (Bash) + workflow self-discipline |
| NO_LAYER_WITHOUT_SCAFFOLD | build | ivy_diagnostics(mode="structural") call before new-layer writes |
| NO_QUALITY_WITHOUT_COVERAGE | review | ivy_coverage / ivy_quality citation at verdict time |
| STALENESS RULE | build, verify, review | ivy_analysis(mode="includes") closure + tool timestamp |

<iron-law name="NO_FIX_WITHOUT_VERIFY" workflow="verify" enforcement="hooks/scripts/block-direct-ivy.sh">

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

<iron-law name="NO_LAYER_WITHOUT_SCAFFOLD" workflow="build" enforcement="ivy_diagnostics(mode=structural) precondition in build Phase 3">

  <instructions>
  Before writing a *net-new* layer file (e.g., creating `quic_8.ivy` when
  `quic_7.ivy` is the latest layer in `{prot}_stack/`), ground the decision
  in `ivy_diagnostics(mode="structural")` returning no
  <severity class="finding" value="ERROR"/>-severity diagnostics for the
  prior layer.
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
  from the current turn inline.
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

<iron-law name="STALENESS_RULE" workflow="build, verify, review" enforcement="ivy_analysis(mode=includes) closure + tool result timestamp">

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
  - **build**: Phase 3 re-runs `ivy_diagnostics(mode="structural")` on a
    predecessor layer if the closure includes a file edited since the
    prior structural pass — the NO_LAYER_WITHOUT_SCAFFOLD gate consumes
    a fresh result, not a cached one.
  - **review**: Phase 2 re-runs `ivy_coverage` / `ivy_quality` before
    emitting a verdict when the spec tree under review has been edited
    since the last coverage snapshot.
  </context>

</iron-law>

<integration
  cited-by="skills/build, skills/verify, skills/review"
  enforcement-hook="hooks/scripts/block-direct-ivy.sh"
  suspended-during="plan mode (navigate Phase 0)"
  re-checked-at="G0 plan-gate on plan approval (navigate Phase 1.5)"/>
