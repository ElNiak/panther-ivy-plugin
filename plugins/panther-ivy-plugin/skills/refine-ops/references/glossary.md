# Verify-ops — glossary

Six terms `verify-ops` uses without further definition. Each is a calibrated word with a fixed meaning in the plugin; do not paraphrase.

| Term | Definition |
|---|---|
| `SOUND` | Calibrated verdict from a quality gate (G0-G6) — the tool result and the critic vote agree the property holds. Matches the gate-verdict severity system (see `.claude/rules/ivy-formatting.md` §"Severity Systems" for the three orthogonal severity systems and how SOUND fits the gate-verdict one). |
| `ABSTAIN` | First-class gate-verdict output: insufficient evidence. NOT a synonym for WARN, UNSURE, or "proceed cautiously." On ABSTAIN, the workflow proceeds to its diagnose phase using `abstain_reason` as the starting hypothesis; it does not treat the upstream tool result as authoritative. |
| MPE | Multi-Perspective Exploration: dispatch N parallel `Explore` agents (Conservative Architect / Pragmatic Engineer / Adversarial Auditor or similar role split) on independent slices of the same context, then aggregate findings. Defined in `cross-cutting-reflection-patterns` Pattern B; composed via `cross-cutting-parallel-dispatch`. |
| Iron law | A binding constraint with a deterministic enforcement site (a hook, a precondition, or a gate-citation requirement). The four iron laws are documented canonically in `.claude/rules/iron-laws.md`; each rigid ops-skill inlines a 1-2 sentence summary plus a pointer to the canonical wording. |
| Knowledge gate | A phase-boundary checkpoint where the orchestrator dispatches `g-knowledge-critic` ×3 in parallel (G6) to vote on whether session learnings are worth persisting (rules, references, feedback memory). Knowledge gates fire after Phase 4 (verify) and before workflow-completion. |
| `pending_dispatch` | Journal event (`workflow_state.append_pending_dispatch`) used to hand off control to another workflow across a turn boundary. The emitter writes the event then clears its `active-workflow` flag; the orchestrator consumes the event on the next turn. The journal record is load-bearing for `/nct-observability` and the agent-dispatch / mcp-tool-reliability recovery contracts. |
