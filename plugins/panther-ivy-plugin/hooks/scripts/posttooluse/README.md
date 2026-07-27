# posttooluse/

PostToolUse hooks split by purpose: structural linters under `lint/` and
adversarial gate dispatchers under `gates/`.

| Subdir | Purpose |
|---|---|
| [`gates/`](gates/) | G2 / G3 / G5 adversarial gate dispatchers. `run-gate.py --id g2`, `--id g3`, and `--id g5` share the dispatcher logic in `gate_handlers.py` (PR3 deduped these from three separate scripts). |
| [`lint/`](lint/) | `ivy.py` — post-write `.ivy` structural lint. `python-format.py` — ruff auto-fix on `.py` writes. |

Direct files:

- `__init__.py` — empty namespace marker so `from posttooluse.gates.X import Y` resolves at import time.

See `.claude/rules/iron-laws.md` for the role of G2 / G3 / G5 gates in the
scaffold and refine workflows, and `.claude/rules/output-style.md` for
the `[G2/G3/G5 ... gate]` systemMessage prefix table.
