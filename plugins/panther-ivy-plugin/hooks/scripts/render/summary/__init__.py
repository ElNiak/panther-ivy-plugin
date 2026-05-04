"""Stop hook: workflow-aware session summary (package).

The entry point lives in :mod:`render.summary.main` and is invoked by the
Stop hook registered in ``hooks/hooks.json`` as
``python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render/summary/main.py``.
The helpers (lint, claim counting, tool metrics, journal audit) live in
:mod:`render.summary.helpers`.

Re-exports are intentionally lazy via ``__getattr__`` so importing this
package does NOT eagerly import :mod:`render.summary.main`. The script
entry point loads ``main`` itself as ``__main__``; eagerly re-importing it
through the package would cause the module to execute twice (once as
``__main__`` and once as ``render.summary.main``).
"""

__all__ = ["build_summary", "main"]


def __getattr__(name):
    if name in ("build_summary", "main"):
        from . import main as _main
        return getattr(_main, name)
    raise AttributeError(f"module 'render.summary' has no attribute {name!r}")
