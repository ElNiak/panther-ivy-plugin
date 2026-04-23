---
paths: ["**/*.ivy", "**/*.spec"]
---

## Iron Laws (build, verify, review workflows)

These four guidelines are cited by the `build`, `verify`, and `review` skills. The deterministic enforcement layer is the project-scoped `PreToolUse` hook at `hooks/scripts/block-direct-ivy.sh` (registered in `hooks/hooks.json` for the `Bash` matcher), which warns (exit 0) about direct CLI invocations of `ivyc`, `ivy_check`, `ivy_show`, and `ivy_to_cpp` and suggests their MCP equivalents — see `ivy-toolkit/SKILL.md` Enforcement section. The text below is the canonical guidance; the workflow skills do not duplicate it.

These guidelines are suspended during plan authoring (when the `navigate` skill detects plan mode). The G0 plan-gate enforces conformance when a plan is approved and the workflow re-activates at Phase 1.5.

### NO_FIX_WITHOUT_VERIFY (verify skill)

Before proposing a *concrete code-edit fix* (an Edit/Write tool call, or a diff offered to the user) for a verification failure, ground it in the relevant verification check from the current turn: `ivy_verify` for end-of-phase verdicts, or `ivy_compile` + IUT during the dev iteration loop (per `feedback_ivy_verify_slow.md` — formal verification is deferred to end-of-phase + background; compile + IUT carries iteration). Cite which check ran when proposing the fix.

**Allowed without prior verify** (these are upstream activities that produce the fix proposal, not the proposal itself):

- The `ivy-debugging-methodology` pre-fix research workflow.
- Hypothesis generation, root-cause analysis, naming candidate edit sites.
- Reading code, running `ivy_diagnostics`, looking up symbols via LSP.
- Comment-only edits and RFC bracket-tag annotations that don't change `before`/`after`/`invariant`/`require`/`ensure` logic.

### NO_LAYER_WITHOUT_SCAFFOLD (build skill)

Before writing a *net-new* layer file (e.g., creating `quic_8.ivy` when `quic_7.ivy` is the latest layer in `{prot}_stack/`), ground the decision in `ivy_diagnostics(mode="structural")` returning no `ERROR`-severity diagnostics for the prior layer.

**Out of scope** (free to author without a structural pass):

- Patches to existing layer files (bug fixes, refactors, additions to a layer that already compiles structurally).
- Authoring entity, shim, test, or utility files outside `{prot}_stack/`.
- Sketching a new layer in a draft file outside the workspace's discovery path.

"No `ERROR`-severity" means the diagnostics array contains no entry with `severity == "error"`. `warning` and `info` entries do not block.

### NO_QUALITY_WITHOUT_COVERAGE (review skill)

Before stating a *formal coverage or quality verdict* — claims like "this model is X% complete", "this isolate has insufficient guards", "the requirement set is fully covered", or any pass/fail judgment on a coverage or quality dimension — cite `ivy_coverage` and/or `ivy_quality` output from the current turn inline.

**Not "quality verdicts" under this guideline** (judgment space, no tool citation required):

- Style and naming feedback ("consider renaming this action").
- Readability and structural clarity comments.
- RFC-alignment phrasing suggestions or comment-quality observations.
- Discussions of design alternatives where no formal pass/fail is asserted.

If the assessment is qualitative ("looks reasonable") it is not a quality verdict. If it asserts a measured property of the model, cite the tool output that supports it.

### STALENESS RULE (applies to all three above)

A tool result for file `F` is *stale* if `F` itself or any file in `F`'s transitive include closure was modified after the tool result's recorded timestamp. The closure is the set returned by `ivy_analysis(mode="includes", relative_path=F)`.

- Edits to workspace files outside `F`'s include closure do not invalidate the result.
- The recorded timestamp is whatever the tool returns (commonly `started_at` for `ivy_verify`; if absent, treat the result's age as zero only for the current turn).
- A workflow dispatched via `pending_dispatch` is a new causal frame; prior tool results in the emitting workflow remain valid unless the dispatched workflow edits files in the emitting workflow's include closure.
- Stale results don't count as evidence — re-run the relevant tool before claiming PASS, transitioning phases, or proposing a concrete patch.
- If `ivy_analysis(mode="includes")` is unavailable in the current session, fall back to workspace-wide invalidation and note the conservative scope when citing the result.
