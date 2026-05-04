# posttooluse/gates/

PostToolUse gate dispatchers for the G2 / G3 / G5 quality gates.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `g2-modeling.py` | PostToolUse | `Write\|Edit` | G2: model-modification gate; appends `gate_dispatched(g2)` on relevant edits. |
| `g3-testspec.py` | PostToolUse | `Write\|Edit` | G3: test-spec-modification gate. |
| `g5-trace.py` | PostToolUse | `ivy_iut_test` | G5: trace-analysis gate after IUT runs. |

PR3 collapses these three into a parametric `run-gate.py` + `registry.py`.

See `.claude/rules/journaling-contract.md` §3 for the `gate_dispatched` event schema.
