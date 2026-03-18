# Ivy Workflow Anti-Patterns

## Rationalization Prevention Table

| Rationalization | Reality |
|---|---|
| "Just a quick fix" | Even single assertions need Phase 1 context — new includes may have been added |
| "I already know the spec" | Run spec-analyst anyway — includes, coverage, and dependencies change between sessions |
| "Verification takes too long" | Skipping verification costs 3-10x more time debugging broken specs later |
| "The user wants it fast" | Fast mode exists for that (/nct-check, /nct-model-info). Deep mode means discipline. |
| "It's just one layer" | One layer change can break downstream includes and invalidate invariants |
| "I'll verify later" | "Later" becomes "never". Verify after EVERY write phase. |
| "The lint passed, that's enough" | Lint catches syntax. ivy_verify catches logical errors. Both are required. |
| "This is a simple rename" | Renames propagate through include chains. Phase 1 (Explore) reveals the impact. |

## Red Flags — STOP Immediately

If you catch yourself thinking any of these, STOP and return to the appropriate phase:

1. **Writing code without having explored** — Return to Phase 1
2. **Creating files without a user-approved plan** — Return to Phase 2
3. **Moving to the next layer without user review** — Wait for Phase 3 gate
4. **Claiming "verification passed" without running ivy_verify** — Run it now
5. **Attempting a 4th fix without escalating** — STOP and present to user
6. **Compiling without passing verification** — Return to Phase 4
7. **Skipping the traceability audit** — Phase 5 is not optional
8. **Using bash ivy_check instead of MCP ivy_verify** — Use ivy-toolkit tools

## Context Decay Warning

Specifications change between sessions. Even if you "know" the codebase:
- New includes may have been added
- Invariants may have been strengthened
- Coverage may have changed
- Dependencies may have shifted

Phase 1 (Explore) prevents acting on stale understanding.
