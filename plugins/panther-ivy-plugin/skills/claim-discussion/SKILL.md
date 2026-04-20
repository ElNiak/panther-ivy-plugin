---
name: claim-discussion
description: "Decision trees for resolving verification and coverage claims. Use when ivy_verify returns FAIL, ivy_coverage shows gaps, or model-reviewer reports issues."
user-invocable: false
context: fork
---

# Claim Discussion

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

Structured discussion templates for resolving verification claims, RFC mapping decisions, and coverage gap priorities. Select the template matching your trigger.

## Template Selection

| Trigger | Template |
|---------|----------|
| `ivy_verify` FAIL or model-reviewer ERROR | `references/verification-claim.md` |
| `ivy_extract_requirements` or RFC mapping | `references/mapping-claim.md` |
| `ivy_coverage(mode="gaps")` shows uncovered reqs | `references/coverage-claim.md` |

After identifying the matching trigger above, Load the corresponding file: `references/verification-claim.md`, `references/mapping-claim.md`, or `references/coverage-claim.md`.

## Persistence — Inline Resolution Comments

All claim discussion outcomes are recorded as inline comments in `.ivy` files:

```ivy
require conn_state = open;  # [rfc9000:4.1] RESOLVED(2026-03-18): Confirmed spec-correct per user
```

| Prefix | Meaning |
|--------|---------|
| `RESOLVED({date})` | Claim discussed and confirmed correct |
| `IUT_FINDING({date})` | IUT non-compliance identified |
| `GUARD_ADDED({date})` | Generation guard added per discussion |
| `DEFERRED({date})` | Decision postponed with reason |
| `KNOWN_DEVIATION({date})` | IUT intentionally diverges from spec |
| `N/A({date})` | Requirement not applicable with reason |

### Rules
- Always include the date in ISO format (YYYY-MM-DD)
- Keep comments concise (one line)
- Place on the same line as the assertion when possible
- Never remove existing resolution comments — append if revisiting

## Integration
- **USED BY:** spec-analyst/model-reviewer agents (typically during orchestrator Phase 4)
- **USED BY:** /nct-check command — for interactive claim discussion after verification
- **PREREQUISITES:** counterexample-guide

## Related Skills
- **`counterexample-guide`** — Technical trace interpretation for verification failures
- **`methodology-reference`** — Verification cycle and quality gate context
