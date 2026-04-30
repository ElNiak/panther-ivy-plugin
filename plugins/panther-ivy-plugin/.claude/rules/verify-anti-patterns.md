---
description: Verify workflow anti-patterns (Red Flags). Auto-loads on verify-ops skill entry. Each row pairs a tempting thought with the calibrated correct behavior. Skill body is leaner because this content lives here, not duplicated in SKILL.md.
paths: ["**/skills/verify-ops/SKILL.md"]
---

<purpose>
Verify-workflow anti-patterns formerly inline as the `## Red Flags` table in
`skills/verify-ops/SKILL.md`. Promoted to an auto-loaded rule so the skill
body stays focused on phase mechanics; the anti-pattern catalog auto-loads
on every verify-ops skill entry.
</purpose>

## Red Flags — Verify

| Thought | Reality |
|---|---|
| "ivy_verify returned SOUND, we're done" | G4 critic verdict required before any claim. SOUND alone is necessary but not sufficient — whitelisted `assume`, trusted-isolate leak, or solver wall-timeout masquerade can produce false SOUND. The verifier agent dispatches G4 inline. |
| "The IUT trace matches the Ivy log, skip pcap" | Ivy log events do not guarantee wire transmission. Always cross-validate via pcap (G5 catalog `#501`). |
| "This counterexample is a model bug, not the IUT" | Distinguish IUT bug vs. model bug via the G5 trace gate (`#505`). Do not classify without the gate. |
| "I can fix the failure without re-verifying" | `NO_FIX_WITHOUT_VERIFY`: every fix loops back through Phase 3 (compile) and Phase 4 (verify). No claim of resolution without fresh tool output. |
| "Three failed attempts, one more should do it" | Phase 7 caps fix attempts at 3 per test file. Above the cap, present the escalation menu — do not silently retry. The cap is journaled via `progress{kind: fix_attempt}` for cross-session accountability. |
| "G4 will fire from the post-tool hook, I'll just keep moving" | The verifier dispatches G4 inline after every `ivy_verify` return. The hook backstop fires too, but inline dispatch is what the workflow consumes for its verdict; the hook protects against agent-side omission only. |
