---
description: Build workflow anti-patterns (Red Flags). Auto-loads on scaffold-ops skill entry. Each row pairs a tempting thought with the calibrated correct behavior. Skill body is leaner because this content lives here, not duplicated in SKILL.md.
paths: ["**/skills/scaffold-ops/SKILL.md"]
---

<purpose>
Build-workflow anti-patterns formerly inline as the `## Red Flags` table in
`skills/scaffold-ops/SKILL.md`. Promoted to an auto-loaded rule so the skill
body stays focused on phase mechanics; the anti-pattern catalog auto-loads
on every scaffold-ops skill entry.
</purpose>

## Red Flags — Build

| Thought | Reality |
|---|---|
| "Layer compiles cleanly, structural check is overkill" | `NO_LAYER_WITHOUT_SCAFFOLD` binds `ivy_diagnostics(mode="structural")` on the predecessor layer before any Write/Edit on layer N. Compile success is necessary but not sufficient. |
| "I can guess which layers from the 14-template" | The methodology branch (NCT / NACT / NSCT) selects layer order. Load `Skill(skill="panther-ivy-plugin:specification-patterns")` and `Skill(skill="panther-ivy-plugin:methodology")` rather than guessing. |
| "I'll fix the [GAP] marker later, layer N+1 first" | Resolve every open `[GAP: #NN]` marker across the current Phase 3 lifecycle BEFORE starting the next layer. Each marker is fixed in place or promoted to `// DEFERRED YYYY-MM-DD`. |
| "The RFC quote feels right from memory" | Always Read the RFC source via the `ivy-refiner-agent` agent or the `methodology` skill. Never paraphrase or quote normative text from memory. |
| "G2 will fire from the post-write hook, I'll just keep writing" | The builder dispatches G2/G3 inline after each Write/Edit on `.ivy`. The `posttooluse/gates/g2-modeling.py` hook is a backstop, not the primary trigger. Inline dispatch produces the asymmetric-vote verdict the workflow consumes. |
| "Verify failed once — bypass and ship" | Build hands off to verify via `pending_dispatch`; on verify failure the orchestrator returns control to Phase 5. Read the journal `gate_verdict`/`progress` entries before re-entering. |
| "RFC requirements feel covered" | Run `ivy_extract_requirements` and compare against bracket-tag annotations. Do not assert coverage without measurement. Scaffold Phase 2 owns the RFC scope; coverage assertions later in review must trace back to a measured manifest. |
| "Just accept inline-fix patches from review without re-running G2/G3" | Review is for audit, not construction. When review hands back via `pending_dispatch(target_workflow="scaffold", phase_hint="layer-check")`, scaffold MUST re-run G2/G3 on the changed layer. G2/G3 are scaffold-time gates and do not fire on review-inline edits. |
