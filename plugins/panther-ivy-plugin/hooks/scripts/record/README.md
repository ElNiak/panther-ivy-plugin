# record/

Hooks that record events into the workflow journal and JSONL side-channels.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `askuserquestion.py` | PostToolUse | `AskUserQuestion` | Record question/answer payloads to JSONL + journal pointer. |
| `workflow-error.py` | PostToolUse | `ivy_*` | Record `error` and G4 `gate_dispatched` journal events. |
| `skill-invocation.py` | PostToolUse | `Skill` | Record `progress{kind: skill_invoked}` for ops-skill dispatches. |
| `session-end.py` | Stop | (none) | Append `session_end` event + rotate journal. |

See `.claude/rules/journaling-contract.md` for the event payload schemas.
