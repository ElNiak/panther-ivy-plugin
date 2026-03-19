"""Validate structural correctness of plugin manifests and configuration files.

These tests ensure that plugin.json, hooks.json, .mcp.json, and the sibling
.lsp.json all have the required fields and that referenced file paths exist.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ===================================================================
# plugin.json
# ===================================================================


class TestPluginJson:
    """Validate .claude-plugin/plugin.json has required fields."""

    def test_plugin_json_exists(self, plugin_root):
        path = plugin_root / ".claude-plugin" / "plugin.json"
        assert path.is_file(), f"plugin.json not found at {path}"

    def test_required_fields_present(self, plugin_root):
        path = plugin_root / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text())

        assert "name" in data, "plugin.json missing 'name' field"
        assert "version" in data, "plugin.json missing 'version' field"
        assert "description" in data, "plugin.json missing 'description' field"

    def test_name_is_nonempty_string(self, plugin_root):
        data = json.loads(
            (plugin_root / ".claude-plugin" / "plugin.json").read_text()
        )
        assert isinstance(data["name"], str) and len(data["name"]) > 0

    def test_version_looks_like_semver(self, plugin_root):
        data = json.loads(
            (plugin_root / ".claude-plugin" / "plugin.json").read_text()
        )
        version = data["version"]
        parts = version.split(".")
        assert len(parts) >= 2, f"Version '{version}' should be semver-like (X.Y or X.Y.Z)"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' is not numeric"


# ===================================================================
# hooks.json
# ===================================================================


class TestHooksJson:
    """Validate hooks/hooks.json structure and referenced scripts."""

    VALID_EVENT_NAMES = {
        "PreToolUse", "PostToolUse", "PostToolUseFailure",
        "SessionStart", "SessionEnd",
        "Stop", "SubagentStart", "SubagentStop",
        "PreCompact", "UserPromptSubmit",
        "Notification", "PermissionRequest",
    }

    def test_hooks_json_exists(self, plugin_root):
        path = plugin_root / "hooks" / "hooks.json"
        assert path.is_file(), f"hooks.json not found at {path}"

    def test_valid_event_names(self, plugin_root):
        data = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text()
        )
        assert "hooks" in data, "hooks.json missing top-level 'hooks' key"
        for event_name in data["hooks"]:
            assert event_name in self.VALID_EVENT_NAMES, (
                f"Unknown hook event name '{event_name}'. "
                f"Valid: {self.VALID_EVENT_NAMES}"
            )

    def test_all_expected_events_present(self, plugin_root):
        data = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text()
        )
        for event_name in self.VALID_EVENT_NAMES:
            assert event_name in data["hooks"], (
                f"Expected event '{event_name}' not found in hooks.json"
            )

    def test_script_paths_reference_existing_files(self, plugin_root):
        """Every hook command references a script via
        ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh -- verify those files
        exist relative to the plugin root."""
        data = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text()
        )
        for event_name, entries in data["hooks"].items():
            for entry in entries:
                hooks_list = entry.get("hooks", [])
                for hook in hooks_list:
                    command = hook.get("command", "")
                    # Extract the script path from the command template
                    # Format: "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh"
                    if "${CLAUDE_PLUGIN_ROOT}" in command:
                        relative = command.split("${CLAUDE_PLUGIN_ROOT}/", 1)[1]
                        script_path = plugin_root / relative
                        assert script_path.is_file(), (
                            f"Hook script not found: {script_path} "
                            f"(referenced in {event_name} hook)"
                        )

    def test_hooks_have_type_and_command_or_prompt(self, plugin_root):
        """Each hook entry must have 'type' and either 'command' or 'prompt'."""
        data = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text()
        )
        for event_name, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    assert "type" in hook, (
                        f"Hook in {event_name} missing 'type' field"
                    )
                    if hook["type"] == "prompt":
                        assert "prompt" in hook, (
                            f"Prompt hook in {event_name} missing 'prompt' field"
                        )
                    else:
                        assert "command" in hook, (
                            f"Hook in {event_name} missing 'command' field"
                        )

    def test_hooks_have_timeout(self, plugin_root):
        """Each command hook entry should have a 'timeout' field."""
        data = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text()
        )
        for event_name, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    if hook.get("type") == "prompt":
                        continue  # Prompt hooks don't need timeouts
                    assert "timeout" in hook, (
                        f"Hook in {event_name} missing 'timeout' field"
                    )
                    assert isinstance(hook["timeout"], int), (
                        f"Hook timeout in {event_name} should be an integer"
                    )


# ===================================================================
# .mcp.json
# ===================================================================


class TestMcpJson:
    """Validate .mcp.json has the ivy-tools MCP server entry."""

    def test_mcp_json_exists(self, plugin_root):
        path = plugin_root / ".mcp.json"
        assert path.is_file(), f".mcp.json not found at {path}"

    def test_has_ivy_tools_server(self, plugin_root):
        data = json.loads((plugin_root / ".mcp.json").read_text())
        assert "mcpServers" in data, ".mcp.json missing 'mcpServers' key"
        assert "ivy-tools" in data["mcpServers"], (
            ".mcp.json missing 'ivy-tools' entry in mcpServers"
        )

    def test_ivy_tools_has_command(self, plugin_root):
        data = json.loads((plugin_root / ".mcp.json").read_text())
        server = data["mcpServers"]["ivy-tools"]
        assert "command" in server, "ivy-tools server missing 'command' field"
        assert "args" in server, "ivy-tools server missing 'args' field"

    def test_start_script_exists(self, plugin_root):
        """The start script referenced in .mcp.json args should exist."""
        data = json.loads((plugin_root / ".mcp.json").read_text())
        server = data["mcpServers"]["ivy-tools"]
        for arg in server.get("args", []):
            if "${CLAUDE_PLUGIN_ROOT}" in arg:
                relative = arg.split("${CLAUDE_PLUGIN_ROOT}/", 1)[1]
                script_path = plugin_root / relative
                assert script_path.is_file(), (
                    f"MCP start script not found: {script_path}"
                )


# ===================================================================
# .lsp.json (unified plugin)
# ===================================================================


class TestLspJson:
    """Validate the .lsp.json configuration in the unified plugin."""

    def test_lsp_json_exists(self, ivy_lsp_root):
        path = ivy_lsp_root / ".lsp.json"
        assert path.is_file(), f".lsp.json not found at {path}"

    def test_has_ivy_language_entry(self, ivy_lsp_root):
        data = json.loads((ivy_lsp_root / ".lsp.json").read_text())
        assert "ivy" in data, ".lsp.json missing 'ivy' language server entry"

    def test_extension_to_language_mapping(self, ivy_lsp_root):
        """The .lsp.json must map .ivy extension to the 'ivy' language."""
        data = json.loads((ivy_lsp_root / ".lsp.json").read_text())
        ivy_config = data["ivy"]
        assert "extensionToLanguage" in ivy_config, (
            ".lsp.json ivy entry missing 'extensionToLanguage'"
        )
        ext_map = ivy_config["extensionToLanguage"]
        assert ".ivy" in ext_map, (
            "extensionToLanguage missing '.ivy' key"
        )
        assert ext_map[".ivy"] == "ivy", (
            f"Expected .ivy -> 'ivy', got .ivy -> '{ext_map['.ivy']}'"
        )

    def test_has_command_and_args(self, ivy_lsp_root):
        data = json.loads((ivy_lsp_root / ".lsp.json").read_text())
        ivy_config = data["ivy"]
        assert "command" in ivy_config, ".lsp.json ivy entry missing 'command'"
        assert "args" in ivy_config, ".lsp.json ivy entry missing 'args'"
