# Hook Scripts

## Naming Convention

- **Hook entry points** (called by `hooks.json`): kebab-case (e.g., `check-mcp-health.py`)
- **Importable Python libraries** (shared utilities): snake_case per PEP 8 (e.g., `hook_utils.py`)
- **Observability subsystem** (`observability/`): snake_case for all files

This matches the Claude Code plugin convention (kebab-case for user-facing components)
while following Python packaging norms for importable modules.
