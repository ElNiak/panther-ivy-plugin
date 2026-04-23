# Shared Iron Laws

This file is referenced (not auto-loaded) by the `build`, `verify`, and `review` skills. It carries no frontmatter and is not a SKILL.md. Each workflow skill cites the laws relevant to it; the deterministic enforcement layer is the project-scoped PreToolUse hook that blocks direct CLI invocations of `ivyc`, `ivy_check`, `ivy_show`, and `ivy_to_cpp` (see `ivy-toolkit/SKILL.md` Enforcement section).

## NO_FIX_WITHOUT_VERIFY (verify skill)

A fix proposal is admissible only if `ivy_verify` has been run on the *current* file state in the same turn. If `ivy_verify` has not yet run, you cannot suggest code changes — run it first, then propose the fix grounded in its diagnostics.

## NO_LAYER_WITHOUT_SCAFFOLD (build skill)

A new layer implementation is admissible only after `ivy_diagnostics(mode="structural")` has passed for the prior layer. If the structural check has not passed, do not write the next layer.

## NO_QUALITY_WITHOUT_COVERAGE (review skill)

Coverage and quality verdicts are admissible only with `ivy_coverage` and `ivy_quality` output cited inline. Impressionistic assessments ("looks good") are not admissible — every claim must point to tool output from this turn.

## STALENESS RULE (applies to all three above)

A tool result is *stale* if any `.ivy` file under the active workspace was modified after the result's `started_at` timestamp. Stale results do not count as evidence — re-run the tool before claiming PASS, transitioning phases, or proposing fixes.
