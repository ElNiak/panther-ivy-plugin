# observability/

JSONL observability subsystem. A single hook (`observe.py`) fires on
every Claude Code event and writes structured records to
`.observability/sessions/<session_id>/events.jsonl` for offline analysis.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `observe.py` | All events | `*` | Emit a JSONL event with tool name, params summary, and tool result excerpt. |

Implementation details:

- The low-level writer lives at `lib/log_event.py`; `observe.py` is the
  hook entry-point that reads the event payload and delegates.
- The write-discipline check at
  `tests/test_observability_write_discipline.py` exempts `observe.py` and
  `lib/log_event.py` from the T1/T2/T3 `systemMessage` templates because
  they fire on every event and would flood the scrollback.

See `.claude/rules/output-style.md` for the systemMessage prefix
conventions and exemption rationale.
