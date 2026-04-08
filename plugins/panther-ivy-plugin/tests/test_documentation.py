"""Validate documentation accuracy.

Ensures that no pre-consolidation MCP tool names appear in any skill, agent,
or command files.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# Tests
# ===================================================================


class TestNoPreConsolidationToolNames:
    """Ensure no pre-consolidation MCP tool names appear in plugin files.

    After the consolidation, tools like ivy_traceability_matrix were merged
    into ivy_coverage, ivy_query, etc. The old names should not appear in
    any skill, agent, or command files.
    """

    # Pre-consolidation tool names that should no longer appear
    PRE_CONSOLIDATION_NAMES = {
        "ivy_traceability_matrix",
        "ivy_requirement_coverage",
        "ivy_coverage_gaps",
        "ivy_cross_references",
        "ivy_impact_analysis",
        "ivy_query_symbol",
        "ivy_action_requirements",
        "ivy_action_dependency_graph",
        "ivy_state_machine_view",
        "ivy_layered_overview",
        "ivy_smart_suggestions",
        "ivy_scaffold_check",
        "ivy_quality_gate",
        "ivy_pattern_analysis",
        "ivy_generate_manifest",
    }

    def _scan_directories(self) -> list[tuple[str, Path, str]]:
        """Scan skills/, agents/, commands/ for pre-consolidation tool names.

        Returns list of (tool_name, file_path, matching_line) tuples.
        """
        hits = []
        scan_dirs = ["skills", "agents", "commands"]
        for dir_name in scan_dirs:
            scan_dir = _PLUGIN_ROOT / dir_name
            if not scan_dir.is_dir():
                continue
            for file_path in scan_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                # Only scan text files
                if file_path.suffix not in {".md", ".txt", ".json", ".yaml", ".yml", ".sh"}:
                    continue
                try:
                    content = file_path.read_text()
                except (UnicodeDecodeError, PermissionError):
                    continue
                for name in self.PRE_CONSOLIDATION_NAMES:
                    if name in content:
                        # Find the line for context
                        for line_num, line in enumerate(
                            content.splitlines(), 1
                        ):
                            if name in line:
                                hits.append((name, file_path, f"L{line_num}: {line.strip()}"))
                                break
        return hits

    def test_no_pre_consolidation_names_in_skills(self):
        """No pre-consolidation tool names should appear in skills/ directory."""
        hits = [
            (name, path, line)
            for name, path, line in self._scan_directories()
            if "skills" in str(path)
        ]
        assert not hits, (
            f"Pre-consolidation tool names found in skills:\n"
            + "\n".join(f"  {name} in {path} ({line})" for name, path, line in hits)
        )

    def test_no_pre_consolidation_names_in_agents(self):
        """No pre-consolidation tool names should appear in agents/ directory."""
        hits = [
            (name, path, line)
            for name, path, line in self._scan_directories()
            if "agents" in str(path)
        ]
        assert not hits, (
            f"Pre-consolidation tool names found in agents:\n"
            + "\n".join(f"  {name} in {path} ({line})" for name, path, line in hits)
        )

    def test_no_pre_consolidation_names_in_commands(self):
        """No pre-consolidation tool names should appear in commands/ directory."""
        hits = [
            (name, path, line)
            for name, path, line in self._scan_directories()
            if "commands" in str(path)
        ]
        assert not hits, (
            f"Pre-consolidation tool names found in commands:\n"
            + "\n".join(f"  {name} in {path} ({line})" for name, path, line in hits)
        )
