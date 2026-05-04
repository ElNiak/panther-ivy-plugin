# posttooluse/gates/

Parametric PostToolUse gate dispatcher for the G2 / G3 / G5 quality gates.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `registry.py` | (data) | — | Declarative `Gate` entries — id, watched_tools, workflow_required, handler refs. Adding a gate is one entry here plus matching handlers in `gate_handlers.py`. |
| `gate_handlers.py` | (data) | — | Per-gate `parse_<id>`, `predicate_<id>`, and `dispatch_<id>` handlers. `dispatch_<id>` owns the `additionalContext` directive prose, the `gate_dispatched` journal payload, and the T2 `systemMessage`. |
| `run-gate.py --id g2` | PostToolUse | `Write\|Edit` | G2 modeling gate (scaffold-only). |
| `run-gate.py --id g3` | PostToolUse | `Write\|Edit` | G3 test-spec gate (scaffold-only). |
| `run-gate.py --id g5` | PostToolUse | `ivy_iut_test` | G5 trace-analysis gate (no workflow constraint). |

The parametric runner threads a single `ctx` dict through the per-gate
handler pipeline: tool-name match → `parse_input` → `predicate` →
workflow gate (if `workflow_required`) → `protocol_dir` resolution →
`dispatch`. Each `dispatch_<id>` appends a `gate_dispatched` journal
event and emits a T2 `systemMessage` (`<event> appended to journal at
<path>`) so the per-file AST-discipline scanners
(`tests/test_hook_output_discipline.py`,
`tests/test_observability_write_discipline.py`) can verify path
construction goes through `journal_path(...)`.

See `.claude/rules/journaling-contract.md` §3 for the `gate_dispatched` event schema.
