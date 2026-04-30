---
description: Review workflow anti-patterns (Red Flags). Auto-loads on review-ops skill entry. Each row pairs a tempting thought with the calibrated correct behavior. Skill body is leaner because this content lives here, not duplicated in SKILL.md.
paths: ["**/skills/review-ops/SKILL.md"]
---

<purpose>
Review-workflow anti-patterns formerly inline as the `## Red Flags` table in
`skills/review-ops/SKILL.md`. Promoted to an auto-loaded rule so the skill
body stays focused on phase mechanics; the anti-pattern catalog auto-loads
on every review-ops skill entry.
</purpose>

## Red Flags — Review

| Thought | Reality |
|---|---|
| "Coverage looks good, skip the citation" | `NO_QUALITY_WITHOUT_COVERAGE`: every verdict MUST cite a fresh `ivy_coverage` / `ivy_quality` tool output. Personal heuristic is not a substitute. |
| "Findings are obvious, skip the MPE roles" | The three MPE roles (Conservative Architect / Pragmatic Engineer / Adversarial Auditor) are the calibrated source. Skipping bypasses the asymmetric-vote discipline and context-isolation invariants. |
| "RFC requirements feel covered" | Run `ivy_extract_requirements` and compare against bracket-tag annotations. Do not assert coverage without measurement. |
| "Just inline-fix the structural issues here" | Review is for audit, not construction. Structural fixes belong in `build` via `pending_dispatch(target_workflow="build", phase_hint="layer-check")`. G2/G3 are build-time gates and will not fire on review-inline edits. |
| "WARNING/INFO findings can be ignored" | They surface in the resolution lifecycle. Mark `// DEFERRED YYYY-MM-DD: <reason>`, do not silently skip. |
| "G5 will fire from the post-tool hook, I'll skip the inline dispatch" | The reviewer dispatches G5 inline on every IUT-test scope. The `assess-trace.py` hook is a backstop only; inline dispatch is what the workflow consumes for its verdict. |
| "Ivy trace shows the event, that's enough" | Ivy log events do NOT guarantee wire transmission. Always cross-validate via pcap (G5 catalog `#501`). |
