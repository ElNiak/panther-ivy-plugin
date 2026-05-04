# session/

SessionStart hooks not covered by another family. The `start/` subdir
hosts the self-test that runs early in the SessionStart sequence.

| Subdir | Purpose |
|---|---|
| [`start/`](start/) | `check-hook-paths.py` — self-test that every `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` path in `hooks.json` resolves on disk. Exits 2 on any missing path. |

The bulk of session-lifecycle work lives elsewhere: workspace detection
in `workspace/detect.py`, stale-state cleanup in `cleanup/`, contract
injection in `journaling/contract-inject.py`. This folder is reserved
for early self-tests that gate the rest of the SessionStart cascade.

See `.claude/rules/journaling-contract.md` §1 for the SessionStart
ordering and `start/README.md` for the self-test details.
