"""Stop hook: workflow-aware session summary (package).

The entry point lives in :mod:`render.summary.main` and is invoked by the
Stop hook registered in ``hooks/hooks.json`` as
``python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render/summary/main.py``.
The helpers (lint, claim counting, tool metrics, journal audit) live in
:mod:`render.summary.helpers`.
"""
