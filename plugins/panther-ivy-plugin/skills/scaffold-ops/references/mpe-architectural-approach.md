# Scaffold — Multi-Perspective Exploration: Architectural Approach

Architectural-approach detail for Phase 1 Step 2 of the scaffold workflow. Read when authoring a new protocol model and needing to choose a model-architecture stance up front.

## Multi-Perspective Exploration — Architectural Approach

After the user confirms the scope, apply the **Multi-Perspective Exploration (MPE)** pattern. Dispatch 3 sibling `Explore` agents in parallel (single message, three `Agent` calls — see `Skill(skill="panther-ivy-plugin:ivy")` `references/parallel-dispatch.md` for the canonical multi-Agent dispatch shape):

- **Exploration question:** "What architectural approach should we use for this [protocol] model?"
- **Agents:**
  - **Conservative Architect** (Explore): Propose a comprehensive model covering all RFC MUST requirements with full invariant coverage. Prioritize correctness over speed.
  - **Pragmatic Engineer** (Explore): Propose a minimal viable model — only the layers needed for the first end-to-end test. Build incrementally.
  - **Adversarial Auditor** (Explore): Propose a security-focused model prioritizing attack surface coverage (NACT-relevant layers, edge cases, error paths).

The user's choice shapes the blueprint in Phase 2.
