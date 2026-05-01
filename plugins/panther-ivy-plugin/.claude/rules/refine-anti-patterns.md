---
description: Refine workflow anti-patterns (Red Flags). Auto-loads on refine-ops skill entry. Each row pairs a tempting thought with the calibrated correct behavior. Skill body is leaner because this content lives here, not duplicated in SKILL.md.
paths: ["**/skills/refine-ops/SKILL.md"]
---

<purpose>
Refine-workflow anti-patterns covering the formal-verification cycle:
compile → ivy_verify → diagnose counterexample → fix loop. Promoted to an
auto-loaded rule so the skill body stays focused on phase mechanics; the
anti-pattern catalog auto-loads on every refine-ops skill entry.
</purpose>

## Red Flags — Refine

| Thought | Reality |
|---|---|
| "ivy_verify returned SOUND, we're done" | G4 critic verdict required before any claim. SOUND alone is necessary but not sufficient — whitelisted `assume`, trusted-isolate leak, or solver wall-timeout masquerade can produce false SOUND. The refiner agent dispatches G4 inline. |
| "I can fix the failure without re-verifying" | `NO_FIX_WITHOUT_VERIFY`: every fix loops back through Phase 3 (compile) and Phase 4 (verify). No claim of resolution without fresh tool output. |
| "Three failed attempts, one more should do it" | Phase 7 caps fix attempts at 3 per test file. Above the cap, present the escalation menu — do not silently retry. The cap is journaled via `progress{kind: fix_attempt}` for cross-session accountability. |
| "G4 will fire from the post-tool hook, I'll just keep moving" | The refiner dispatches G4 inline after every `ivy_verify` return. The hook backstop fires too, but inline dispatch is what the workflow consumes for its verdict; the hook protects against agent-side omission only. |
| "STALENESS_RULE doesn't apply, I just edited one file" | A tool result is stale if any file in the include closure changed since the result's timestamp. Re-run before claiming PASS, transitioning phases, or proposing a concrete patch. |
| "I'll inline-Edit the .ivy file from inside the refiner agent" | The refiner agent has `forbidden_tools: ["Edit","Write"]`. Hand off via `pending_dispatch(scaffold, phase_hint="apply-fix", reason=...)` and let the builder apply the Edit on the next turn. |
| "Coverage looks good, skip the citation" | `NO_QUALITY_WITHOUT_COVERAGE`: every coverage / quality verdict that follows a refine cycle MUST cite a fresh `ivy_coverage` / `ivy_quality` tool output. Personal heuristic is not a substitute. (Folded from review-anti-patterns 2026-05-01: applies whenever refine produces a finding that asserts coverage or quality.) |
| "Findings are obvious, skip the MPE roles" | The three MPE roles (Conservative Architect / Pragmatic Engineer / Adversarial Auditor) are the calibrated source. Skipping bypasses the asymmetric-vote discipline and context-isolation invariants. (Folded from review-anti-patterns 2026-05-01: refine consumes MPE on G4 diagnosis paths and on coverage hand-offs.) |
| "WARNING/INFO findings can be ignored" | They surface in the resolution lifecycle. Mark `// DEFERRED YYYY-MM-DD: <reason>` in the model, do not silently skip. (Folded from review-anti-patterns 2026-05-01.) |
