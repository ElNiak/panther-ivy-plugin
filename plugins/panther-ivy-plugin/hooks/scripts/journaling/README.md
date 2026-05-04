# journaling/

Hooks that maintain the workflow-journal contract.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `contract-check.py` | SessionStart | (none) | Verify the journaling contract file is readable; block dispatch if not. |
| `contract-inject.py` | SubagentStart | (none) | Inject the journaling contract into a dispatched plugin specialist's context. |

See `.claude/rules/journaling-contract.md` for the contract specification.
