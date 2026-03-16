"""Validate documentation accuracy.

Ensures that the tooling-reference SKILL.md lists LSP operations that have
corresponding handler registrations in server.py, and that no pre-consolidation
MCP tool names appear in any skill, agent, or command files.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Root of the panther-ivy-plugin Claude Code plugin
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Root of the ivy-lsp source tree.
# The ivy-lsp package lives as a submodule of panther_ivy, not a sibling
# plugin under plugins/. We walk up from the plugin root to find it:
# panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/
#   .parent.parent.parent -> panther_ivy/submodules/
#   + ivy-lsp/ivy_lsp/ -> the server source code
_SUBMODULES_DIR = _PLUGIN_ROOT.parent.parent.parent
_IVY_LSP_SRC = _SUBMODULES_DIR / "ivy-lsp" / "ivy_lsp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill_md() -> str:
    """Read the tooling-reference SKILL.md content."""
    path = _PLUGIN_ROOT / "skills" / "tooling-reference" / "SKILL.md"
    assert path.is_file(), f"tooling-reference/SKILL.md not found at {path}"
    return path.read_text()


def _extract_lsp_operations_from_skill(text: str) -> set[str]:
    """Extract the list of LSP operations mentioned in the SKILL.md.

    Looks for the **Operations** line which lists them like:
    `goToDefinition`, `findReferences`, `hover`, ...
    """
    operations = set()

    # Find the **Operations** line
    for line in text.splitlines():
        if "**Operations**" in line:
            # Extract backtick-quoted operation names
            ops = re.findall(r"`(\w+)`", line)
            operations.update(ops)
            break

    return operations


def _map_operation_to_lsp_feature(operation: str) -> str | None:
    """Map a SKILL.md operation name to the LSP protocol constant name
    that would appear in a @server.feature() registration.

    Returns None if no mapping is defined (operation may be custom/future).
    """
    mapping = {
        "goToDefinition": "TEXT_DOCUMENT_DEFINITION",
        "findReferences": "TEXT_DOCUMENT_REFERENCES",
        "hover": "TEXT_DOCUMENT_HOVER",
        "documentSymbol": "TEXT_DOCUMENT_DOCUMENT_SYMBOL",
        "workspaceSymbol": "WORKSPACE_SYMBOL",
        "goToImplementation": "TEXT_DOCUMENT_IMPLEMENTATION",
        "prepareCallHierarchy": "TEXT_DOCUMENT_PREPARE_CALL_HIERARCHY",
        "incomingCalls": "CALL_HIERARCHY_INCOMING_CALLS",
        "outgoingCalls": "CALL_HIERARCHY_OUTGOING_CALLS",
    }
    return mapping.get(operation)


def _find_registered_features_in_server() -> set[str]:
    """Scan all .py files under ivy_lsp/ for @server.feature() registrations
    and return the set of feature constant names found.

    Returns strings like 'TEXT_DOCUMENT_DEFINITION', 'WORKSPACE_SYMBOL', etc.
    """
    if not _IVY_LSP_SRC.is_dir():
        pytest.skip(f"ivy-lsp source not found at {_IVY_LSP_SRC}")

    features = set()
    for py_file in _IVY_LSP_SRC.rglob("*.py"):
        content = py_file.read_text()
        # Match patterns like: @server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
        for match in re.finditer(
            r"@server\.feature\(lsp\.(\w+)", content
        ):
            features.add(match.group(1))
        # Also match self.feature() in server.py
        for match in re.finditer(
            r"@self\.feature\(lsp\.(\w+)", content
        ):
            features.add(match.group(1))
    return features


# ===================================================================
# Tests
# ===================================================================


class TestToolingReferenceAccuracy:
    """Verify the tooling-reference SKILL.md matches the ivy-lsp implementation."""

    def test_skill_md_exists(self):
        path = _PLUGIN_ROOT / "skills" / "tooling-reference" / "SKILL.md"
        assert path.is_file()

    def test_lsp_operations_listed(self):
        """SKILL.md should list at least the core LSP operations."""
        text = _read_skill_md()
        operations = _extract_lsp_operations_from_skill(text)
        # At minimum, the core operations should be documented
        core_ops = {"goToDefinition", "findReferences", "hover", "documentSymbol"}
        for op in core_ops:
            assert op in operations, (
                f"Core LSP operation '{op}' not found in SKILL.md Operations list"
            )

    def test_documented_operations_have_handlers(self):
        """Every LSP operation listed in SKILL.md should have a corresponding
        @server.feature() registration in ivy-lsp/server.py (or feature modules).

        Operations that are listed as planned/future but not yet registered
        are tracked separately.
        """
        if not _IVY_LSP_SRC.is_dir():
            pytest.skip("ivy-lsp source not available")

        text = _read_skill_md()
        operations = _extract_lsp_operations_from_skill(text)
        registered = _find_registered_features_in_server()

        # Operations documented in SKILL.md but not yet registered in
        # ivy-lsp. When a new operation gets implemented, the companion
        # test_not_yet_implemented_operations_tracked will fail, prompting
        # removal from this set.
        NOT_YET_IMPLEMENTED: set[str] = set()  # All currently implemented

        missing = []
        for op in operations:
            feature_name = _map_operation_to_lsp_feature(op)
            if feature_name is None:
                # Unknown operation, skip
                continue
            if op in NOT_YET_IMPLEMENTED:
                # Documented as planned but not yet registered
                continue
            if feature_name not in registered:
                missing.append(f"{op} -> {feature_name}")

        assert not missing, (
            f"LSP operations documented in SKILL.md but not registered in "
            f"ivy-lsp server: {missing}"
        )

    def test_all_documented_operations_are_registered(self):
        """Verify that ALL operations documented in SKILL.md are now
        registered in ivy-lsp. This is the inverse of the exclusion-list
        approach: it confirms full coverage.

        If a new operation is added to SKILL.md without a corresponding
        handler, this test will fail (caught by
        test_documented_operations_have_handlers above). This test
        separately confirms that previously-future operations are now
        present.
        """
        if not _IVY_LSP_SRC.is_dir():
            pytest.skip("ivy-lsp source not available")

        registered = _find_registered_features_in_server()

        # All operations that were once planned and are now expected to
        # be registered.
        expected_ops = {
            "goToImplementation": "TEXT_DOCUMENT_IMPLEMENTATION",
            "prepareCallHierarchy": "TEXT_DOCUMENT_PREPARE_CALL_HIERARCHY",
            "incomingCalls": "CALL_HIERARCHY_INCOMING_CALLS",
            "outgoingCalls": "CALL_HIERARCHY_OUTGOING_CALLS",
        }

        missing = []
        for op_name, feature_name in expected_ops.items():
            if feature_name not in registered:
                missing.append(op_name)

        assert not missing, (
            f"These operations are documented in SKILL.md and expected to "
            f"be registered in ivy-lsp, but were not found: {missing}"
        )


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
