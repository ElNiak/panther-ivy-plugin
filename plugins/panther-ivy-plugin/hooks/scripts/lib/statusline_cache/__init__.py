"""Public API for the statusline cache package.

Re-exports the complete surface of the statusline_cache module split
across paths, shared, overlay, and migration sub-modules. Callers that
previously did ``import statusline_cache as sc`` will do
``from lib.statusline_cache import ...`` after T5 rewrites their imports.

Public surface (confirmed against test_statusline_cache_*.py imports):
  - CACHE_VERSION
  - cache_path_for, overlay_path_for
  - update_section, update_sections
  - clear_section, clear_cache
  - update_from_hook, update_sections_from_hook, read_section_from_hook
  - update_overlay, read_overlay, clear_overlay
  - update_overlay_from_hook, read_overlay_from_hook
  - statusline_overlay_load
  - migrate_legacy_cache
  - _cache_root, _workspace_digest, _normalize_active_group, _resolve_active_group
  - _VALID_PATH_COMPONENT_RE, _DEFAULT_GROUP
"""

from lib.statusline_cache.migration import migrate_legacy_cache
from lib.statusline_cache.overlay import (
    clear_overlay,
    read_overlay,
    read_overlay_from_hook,
    statusline_overlay_load,
    update_overlay,
    update_overlay_from_hook,
)
from lib.statusline_cache.paths import (
    CACHE_VERSION,
    _DEFAULT_GROUP,
    _VALID_PATH_COMPONENT_RE,
    _cache_root,
    _normalize_active_group,
    _resolve_active_group,
    _workspace_digest,
    cache_path_for,
    overlay_path_for,
)
from lib.statusline_cache.shared import (
    _SECTIONS_WITH_TIMESTAMP,
    _atomic_write,
    _now_iso,
    _read_cache,
    _resolve_workspace_root,
    _with_cache_lock,
    clear_cache,
    clear_section,
    read_section_from_hook,
    update_from_hook,
    update_section,
    update_sections,
    update_sections_from_hook,
)

__all__ = [
    "CACHE_VERSION",
    "cache_path_for",
    "overlay_path_for",
    "update_section",
    "update_sections",
    "clear_section",
    "clear_cache",
    "update_from_hook",
    "update_sections_from_hook",
    "read_section_from_hook",
    "update_overlay",
    "read_overlay",
    "clear_overlay",
    "update_overlay_from_hook",
    "read_overlay_from_hook",
    "statusline_overlay_load",
    "migrate_legacy_cache",
    # Private symbols accessed directly by tests in the partitioning/migration suites
    "_cache_root",
    "_workspace_digest",
    "_normalize_active_group",
    "_resolve_active_group",
    "_VALID_PATH_COMPONENT_RE",
    "_DEFAULT_GROUP",
    "_SECTIONS_WITH_TIMESTAMP",
    "_read_cache",
    "_atomic_write",
    "_with_cache_lock",
    "_now_iso",
    "_resolve_workspace_root",
]
