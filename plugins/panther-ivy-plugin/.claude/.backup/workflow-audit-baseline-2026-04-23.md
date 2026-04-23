# Workflow-Audit Follow-Ups Baseline — 2026-04-23

Phase 0.1 of the plan at `docs/superpowers/specs/2026-04-23-workflow-audit-followups-tracker.md`.

This file records the classification of all pre-existing working-tree changes in the plugin submodule as of 2026-04-23, and the pass/fail counts of the plugin's test suites before any spec-driven edits. Both inform Phase 9.2's regression check.

## Classification decision

Every `M` and `??` file was inspected (diff or full read) against the seven spec scopes. **Finding**: no current hunk overlaps the sections/lines that any of the seven specs rewrites. Every change is either in a different section of the same file (iron-laws prose rework, shortcut command additions, gate-critic Self-Check, etc.) or entirely outside spec scope.

Consequence: **all M/??/D paths are classified `unrelated` or `delete-intended` for Phase 0.1b's baseline commit.** Spec edits land cleanly on top in Phases 1–8 without needing a three-way merge. The one caveat (the new gate-critic Self-Check section's use of `UNSURE` in `agents/model-reviewer.md`) is tracked in the "Spec-side follow-ups" section below, so Phase 5 (S2) catches it.

## Classification table

| Path (submodule-relative) | Status | Classification | Owner-spec | Rationale |
|---|---|---|---|---|
| `.claude-plugin/marketplace.json` | M | unrelated | — | Top-level marketplace cleanup; removes stale ivy-lsp entry (per CHANGELOG 0.10.0). No spec touches this. |
| `REVIEW.md` | D | unrelated | — | Top-level review doc removal; CHANGELOG notes review-findings deferred to follow-up reliability release. |
| `SKILLS-REVIEW.md` | D | unrelated | — | Same as above. |
| `plugins/ivy-lsp/.lsp.json` | D | unrelated | — | Duplicate lsp config removal (per CHANGELOG 0.10.0). |
| `plugins/panther-ivy-plugin/.claude-plugin/plugin.json` | M | unrelated | — | Plugin-version touch; not a spec concern. |
| `plugins/panther-ivy-plugin/.claude/rules/debugging.md` | D | unrelated | — | Deleted; superseded by `ivy-debugging-methodology` skill. |
| `plugins/panther-ivy-plugin/.claude/rules/ivy-formatting.md` | M | unrelated → S2 extends | S2 | Current M = refinements to existing RFC/citation rules. S2 APPENDS a new "Severity Systems" section after the existing "Self-Review" section. No collision. |
| `plugins/panther-ivy-plugin/.claude/rules/ivy-patterns.md` | M | unrelated | — | +149 lines of new pattern content; unrelated to workflow-audit clusters. |
| `plugins/panther-ivy-plugin/.claude/rules/nct-methodology.md` | M | unrelated | — | +1/−1 touch; S5 reads the NACT table here but does not edit this file. |
| `plugins/panther-ivy-plugin/.claude/rules/tool-reference.md` | D | unrelated | — | Deleted; content subsumed by ivy-toolkit skill. |
| `plugins/panther-ivy-plugin/.mcp.json` | M | unrelated | — | +1/−1 config tweak. |
| `plugins/panther-ivy-plugin/README.md` | M | unrelated → S1 extends | S1 | Current M = reorganized sections. S1 Commit D rewrites the State Management section specifically (drops invocation_depth/caller from the YAML example). No collision with the current M. |
| `plugins/panther-ivy-plugin/agents/model-reviewer.md` | M | unrelated + spec-overlap-note | S2, S6 | Current M = new "Tools-Contract Self-Check (Gate Mode Only)" section at line 188. S2's line-186 `UNSURE→ABSTAIN` change is in the pre-existing content (above the M hunk). S6 appends a Failure Modes section *after* all existing content. **Follow-up**: the Self-Check section uses `UNSURE` on line 196. Phase 5 (S2) must replace that `UNSURE` → `ABSTAIN` in addition to the line-186 fix. Recorded in spec-side follow-ups below. |
| `plugins/panther-ivy-plugin/commands/README.md` | M | unrelated | — | +3/−1 doc touch. |
| `plugins/panther-ivy-plugin/commands/nct-iut-test.md` | M | unrelated → S7 namespace-sweep | S7 | +1/−1; S7 Commit B does a namespace sweep of Skill() calls — will visit regardless. Current content change is independent. |
| `plugins/panther-ivy-plugin/hooks/hooks.json` | M | unrelated | — | +2/−12; hook registration cleanup. |
| `plugins/panther-ivy-plugin/hooks/scripts/check-mcp-health.py` | M | unrelated | — | −54 lines net reduction; simplification. |
| `plugins/panther-ivy-plugin/hooks/scripts/hook_utils.py` | M | unrelated | — | +56 lines; new helper function. S8's validator lives in `workflow_state.py`, not here. |
| `plugins/panther-ivy-plugin/hooks/scripts/observability/observe.py` | M | unrelated | — | +26/−20 observability refactor. |
| `plugins/panther-ivy-plugin/output-styles/*` | M (×3) | unrelated | — | Output-style refinements; no spec touches these. |
| `plugins/panther-ivy-plugin/routing-rules.json` | M | unrelated | — | +1 line: descriptive `_comment` field. S8's validator reads `workflows` key; no collision. |
| `plugins/panther-ivy-plugin/skills/README.md` | M | unrelated | — | +4/−1 navigation touch. |
| `plugins/panther-ivy-plugin/skills/build/SKILL.md` | M | unrelated → S1 rewrites sections + S5 extends | S1, S5 | Current M: (a) "Iron Laws" header rewrite pointing to iron-laws.md rule; (b) Phase 3 Step 3 pattern-#403 phrasing; (c) Phase 4 sub-workflow dispatch rewording (still uses invocation_depth); (d) Integration shortcut command line. S1 Commit C rewrites Phase 4 completely (drops invocation_depth, uses pending_dispatch) — hunk (c) gets cleanly overwritten. S5 Phase 7 extends Phase 2 Step 3 + Phase 6 Step 1 — hunks (a)(b)(d) untouched. No merge conflict expected. |
| `plugins/panther-ivy-plugin/skills/claim-discussion/SKILL.md` | M | unrelated | — | +1/−2 wording touch. |
| `plugins/panther-ivy-plugin/skills/counterexample-guide/SKILL.md` | M | unrelated | — | +3/−1 wording touch. |
| `plugins/panther-ivy-plugin/skills/ivy-debugging-methodology/SKILL.md` | M | unrelated | — | +8/−5; references/debugging-environment.md added per CHANGELOG work. |
| `plugins/panther-ivy-plugin/skills/ivy-toolkit/SKILL.md` | M | unrelated | — | +25/−14 tool-catalog alignment. |
| `plugins/panther-ivy-plugin/skills/ivy-toolkit/references/tool-catalog.md` | M | unrelated | — | +25/−1 tool-catalog updates. |
| `plugins/panther-ivy-plugin/skills/ivy-writing-guide/SKILL.md` | M | unrelated | — | +12/−171 major shrink; content moved to references (CHANGELOG-noted refactor). |
| `plugins/panther-ivy-plugin/skills/knowledge-capture/SKILL.md` | M | unrelated | — | +3/−2 user-invocable upgrade wording. |
| `plugins/panther-ivy-plugin/skills/knowledge-capture/references/knowledge-taxonomy.md` | M | unrelated | — | +2/−2 wording. |
| `plugins/panther-ivy-plugin/skills/methodology-reference/SKILL.md` | M | unrelated → S5 extends | S5 | Current M: (a) expanded 14-layer template cross-reference; (b) NACT section adds a pointer to the new `apt-attack-patterns` skill. S5 adds a *different* Integration pointer to `references/nsct-experiment-template.md`. No collision. |
| `plugins/panther-ivy-plugin/skills/navigate/SKILL.md` | M | unrelated → S1 rewrites sections | S1 | Current M: (a) line ~215 reflection-patterns dispatch wording; (b) line ~466 journal schema cross-reference wording. S1 Commit C rewrites line 63, Phase 1 Step 2c (new), line 111 navigate/init schema, Sub-Workflow Return Rule (lines 438–444), and Task-3/defined-later anchors. **Disjoint** from current M hunks. Clean overlay. |
| `plugins/panther-ivy-plugin/skills/propagation-patterns/SKILL.md` | M | unrelated | — | +2/−2 wording. |
| `plugins/panther-ivy-plugin/skills/review/SKILL.md` | M | unrelated → S1 rewrites sections | S1 | Current M: Iron Laws header rewrite (lines 33–38). S1 Commit C rewrites Phase 1 Step 3 triage preflight (lines 107–117), Phase 3 Step 2 verify follow-up (lines 236–248), line 236 depth guard, On Completion (line 269). **Disjoint** from current M. |
| `plugins/panther-ivy-plugin/skills/session-retrospective/SKILL.md` | D | delete-intended | — | Removed per CHANGELOG 0.10.0 (merged into knowledge-capture). |
| `plugins/panther-ivy-plugin/skills/specification-patterns/SKILL.md` | M | unrelated | — | +3/−28 shrink. |
| `plugins/panther-ivy-plugin/skills/verify/SKILL.md` | M | unrelated → S1 rewrites sections | S1 | Current M: (a) frontmatter description refinement; (b) Iron Laws header rewrite (lines 33–41); (c) Integration shortcut command line. S1 Commit C rewrites Phase 1 Step 1 triage preflight, Phase 4 On PASS review follow-up (lines 218–222), Phase 5 skip-guard deletion (line 252), Phase 6 depth guard removal (line 219). **Disjoint** from current M. |
| `plugins/panther-ivy-plugin/.claude/.backup/rules-2026-04-22/debugging.md` | ?? | unrelated | — | Backup of deleted file; preserve for history per global memory rule (backup before delete). |
| `plugins/panther-ivy-plugin/.claude/.backup/rules-2026-04-22/tool-reference.md` | ?? | unrelated | — | Same as above. |
| `plugins/panther-ivy-plugin/.claude/.backup/skills-2026-04-22/_shared-iron-laws.md` | ?? | unrelated | — | Backup of extracted iron-laws content before refactor. |
| `plugins/panther-ivy-plugin/.claude/rules/iron-laws.md` | ?? | spec-relevant-containing | S1, S3 | Newly authored this session. Line 53 = "A sub-workflow invoked at `invocation_depth > 0` does not invalidate parent-frame results unless it edits files in the closure." **Matches S1's assumption.** S1 Commit B rewrites this line. S3 audits the STALENESS RULE section. Baseline-commit as untracked-to-tracked so S1 Commit B lands cleanly as a diff. |
| `plugins/panther-ivy-plugin/CHANGELOG.md` | ?? | spec-relevant-containing | S1 | Newly authored. Existing entry: 0.10.0 section. S1 Commit E appends a new section for workflow-audit follow-ups. Baseline-commit the 0.10.0 entry first; S1 extends. |
| `plugins/panther-ivy-plugin/hooks/README.md` | ?? | unrelated | — | New README for hooks directory. |
| `plugins/panther-ivy-plugin/hooks/scripts/tests/test_emit_hook_output.py` | ?? | unrelated | — | New test scaffolding. Not for any of the 7 specs. |
| `plugins/panther-ivy-plugin/hooks/scripts/tests/test_mcp_health_state.py` | ?? | unrelated | — | New test scaffolding. |
| `plugins/panther-ivy-plugin/skills/apt-attack-patterns/SKILL.md` | ?? | unrelated | — | New skill, per CHANGELOG NACT pattern library direction. |
| `plugins/panther-ivy-plugin/skills/apt-attack-patterns/references/apt-protocol-binding.md` | ?? | unrelated | — | Same. |
| `plugins/panther-ivy-plugin/skills/apt-attack-patterns/references/attack-stage-examples.md` | ?? | unrelated | — | Same. |
| `plugins/panther-ivy-plugin/skills/ivy-debugging-methodology/references/debugging-environment.md` | ?? | unrelated | — | New reference file backing the M hunk in the parent SKILL.md. |

Total: 40 paths classified. 0 require special three-way merging; 0 require deferral to after spec commits.

## Spec-side follow-ups (injected into spec phase instructions)

Inspection of current M hunks surfaced one behavior adjustment to the spec's as-written edit inventory. Record here so the relevant phase catches it at execution time:

- **Phase 5 (S2) — additional `UNSURE` site in `agents/model-reviewer.md`**: besides the spec's line-186 `UNSURE → ABSTAIN` fix, the current working tree includes a new "Tools-Contract Self-Check (Gate Mode Only)" section whose line 196 also reads "Return `UNSURE` rather than silently widening the tool surface." The baseline commit includes this section as-is. When S2 runs, fix **both** sites (line 186 in the original block AND the new line 196 in the Self-Check section).

## Baseline test counts

Recorded by Phase 0.3 (see task #4). Populated below after the pytest run.

```
pytest tests/ ...
pytest hooks/scripts/tests/ ...
```

(Phase 0.3 will append the tail of each run here.)
