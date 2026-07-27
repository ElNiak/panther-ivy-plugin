# Navigate — Journal Events

Cold-path content extracted from `navigate/SKILL.md`. Documents which journal event types navigate produces or consumes during its lifecycle.

## Journal entry types this skill produces or consumes

| Type | Direction | Introduced by |
|------|-----------|---------------|
| `context_switch` | produces (Phase 0 detection) | Phase 0 |
| `plan_approved` | produces (Plan-Author Step 4) | Plan-Author Branch |
| `pending_dispatch` | consumes (Phase 1 Step 2c) | Any workflow emitting a hand-off |
| `workflow_resumed` | produces (Phase 1 Step 2c + Phase 1.5 Step 5) | Pending-dispatch consumption + post-plan-approval handoff |
| `gate_verdict` with `gate: "g0"` | produces (Phase 1.5, via `reflection-patterns` G0 dispatch) | Post-plan-approval handoff |
| `decision`, `phase_transition`, `session_start`, `session_end`, `error`, `progress` | both | Existing schema (unchanged) |

Full schema for each type lives in the `reflection-patterns` skill's `references/gates.md` (`gate_verdict` payload) and in `superpowers:writing-plans` (plan file conventions consumed by the `supersedes` extraction, when that plugin is installed).
