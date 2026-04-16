# Hook Lifecycle Reference

Full tool invocation pipeline for the panther-ivy-plugin. Source of truth for which tools are hook-rendered vs. raw, and when each hook fires.

## Lifecycle Diagram

```
User prompt → UserPromptSubmit hooks → Claude selects tool
  → PreToolUse hooks → Tool execution → PostToolUse hooks → Result to Claude
```

## UserPromptSubmit Hooks

Fire before Claude processes each user message. No matcher — apply to every prompt.

| Hook | Effect |
|------|--------|
| compose-style.py | Reads active workflow overlay and injects it as a system prompt prefix, overriding output-style defaults for the current phase |
| route-user-prompt.py | Maps user intent to the active workflow skill; activates the matching workflow if none is active |
| observe.py --event UserPromptSubmit | Observability: records prompt metadata to JSONL session log |

## SessionStart Hooks

Fire once when the Claude Code session starts. No matcher.

1. `cleanup-stale-pids.sh` — removes leftover PID files from previous sessions
2. `cleanup-stale-workflow.py` — clears stale `active-workflow` flags older than the session
3. `detect-ivy-workspace.sh` — auto-detects `.ivyworkspace` markers and restores the previous workspace scope
4. `wait-for-indexing.sh` — waits up to 20s for the LSP index to be ready before the first tool call
5. `observe.py --event SessionStart` — observability: records session start metadata

## PreToolUse Hooks

Fire after Claude selects a tool but before execution. A hook that exits with code 2 blocks the tool call.

| Hook | Applies to | Effect |
|------|-----------|--------|
| block-direct-ivy.sh | `Bash` commands containing `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` | Blocks with error message; enforces MCP-only usage (CLI lacks staging and include setup) |
| check-workspace-scope.py | `Write` or `Edit` on `.ivy` files | Blocks writes to files outside the active workspace; reads across workspaces are always allowed |
| ivy_verify prompt tip | `ivy_verify` | Injects prompt: "Consider running ivy_diagnostics(mode=\"structural\") first for fast structural validation" |
| ivy_coverage prompt tip | `ivy_coverage` | Injects prompt: scope with `test_file`, run diagnostics first, use mode=stats before mode=matrix |
| check-mcp-health.py | Any `mcp__.*ivy` tool | Validates the MCP server is alive; blocks if server is unreachable |
| check_lsp_log.py | Any `mcp__.*ivy` tool | Checks LSP log for indexing-in-progress signal; blocks if indexing is not yet complete |
| check-indexing-ready.sh | Any `mcp__.*ivy` tool | Secondary indexing readiness check via shell |
| observe.py --event PreToolUse | `mcp__`, `Bash`, `Write`, `Edit`, `Agent` | Observability: records tool selection and parameters |

## PostToolUse Hooks

Fire after tool execution, before the result is returned to Claude.

| Hook | Applies to | Effect |
|------|-----------|--------|
| render-tool-result.py | `ivy_verify`, `ivy_coverage`, `ivy_diagnostics`, `ivy_compile`, `ivy_quality` | Reformats raw JSON result to workflow-appropriate prose or tables; style adapts to active overlay |
| post-write-ivy-lint.sh | `Write` or `Edit` on `.ivy` files | Runs `ivy_diagnostics(mode="structural")` automatically after every Ivy file save |
| post-write-workflow-aware.py | `Write` or `Edit` | Workflow-aware post-write processing (phase tracking, build-state updates) |
| interaction-checkpoint.py | `ivy_verify`, `ivy_coverage`, `ivy_extract_requirements`, `ivy_quality` | Records interaction checkpoint for session continuity |
| track-workflow-skill.py | `Skill` invocations | Records phase transitions to the workflow journal |
| auto-load-skill-references.py | `Skill` invocations | Injects relevant reference files into context after skill activation |
| record-workflow-error.py | `ivy_verify`, `ivy_compile`, `ivy_diagnostics`, `ivy_coverage`, `ivy_iut_test`, `ivy_quality` | Captures tool errors to the session error log for debugging |
| observe.py --event PostToolUse | `mcp__`, `Bash`, `Write`, `Edit`, `Agent` | Observability: records tool result metadata |

## Rendering Rules

### Rule 1: Do NOT reformat hook-rendered tools

These tools have a PostToolUse formatter (`render-tool-result.py`) that already converts JSON to formatted output. Adding a second formatting pass will duplicate or corrupt the result:

- `ivy_verify`
- `ivy_compile`
- `ivy_diagnostics`
- `ivy_coverage`
- `ivy_quality`

### Rule 2: DO format raw tools

All other MCP tools return raw JSON. Format their results as formatted prose or tables per `ivy-formatting.md`. Never emit raw JSON to the user.

### Rule 3: Rendering style follows workflow overlay

`render-tool-result.py` reads the active workflow overlay (set by `compose-style.py` on each prompt) to choose verbosity, structure, and tone. The same verification failure renders differently in the `verify` workflow (diagnostic prose) versus the `review` workflow (summary table).

## Rendered Tools — Source of Truth

The `rendering` field in `_TOOL_METADATA` (`ivy_lsp/mcp/tools/__init__.py`) is the authoritative list of which tools are hook-rendered. The table below is derived from it.

| Rendering | Tools |
|-----------|-------|
| `hook` | ivy_verify, ivy_compile, ivy_diagnostics, ivy_coverage, ivy_quality |
| `raw` | All other MCP tools (ivy_model_info, ivy_include_graph, ivy_capabilities, ivy_scope, ivy_extract_requirements, ivy_manifest, ivy_rfc_get, ivy_rfc_search, ivy_rfc_section, ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold, ivy_find_variants, ivy_serdes_correlation, ivy_change_impact, ivy_workspace, ivy_workflow_state, ivy_health_check, ivy_index, ivy_verification_dashboard, ivy_iut_test) |

## Stop / SessionEnd Hooks

| Event | Hook | Effect |
|-------|------|--------|
| Stop | record-session-end.py | Finalizes session log entry |
| Stop | render-summary.py | Renders session summary (workflow phases completed, errors encountered) |
| Stop | observe.py --event Stop | Observability: records session end |
| SessionEnd | cleanup-ivy-lsp.sh | Stops the LSP server and cleans up socket/PID files |
| SessionEnd | observe.py --event SessionEnd | Observability: records session end metadata |
