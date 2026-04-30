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
| observe.py --event UserPromptSubmit | Observability: records prompt metadata to JSONL session log |

(The pre-Phase-E `compose-style.py` and `route-user-prompt.py` hooks were removed; intent classification now lives in the orchestrator skill `skills/ivy/SKILL.md`, and style composition is driven by `.claude/rules/output-style.md` and the per-skill body, not a separate hook.)

## SessionStart Hooks

Fire once when the Claude Code session starts. No matcher. Ordering matters: `detect-ivy-workspace.sh` (step 3) exports `IVY_WORKSPACE_ROOT`, `IVY_MCP_LOG_PATH`, `IVY_LSP_LOG_PATH`, and related env vars; `wait-for-indexing.sh` (step 5) consumes them. Reordering these two breaks env-var propagation and causes `wait-for-indexing.sh` to fall back to `/tmp` defaults.

1. `cleanup-stale-pids.sh` — removes leftover PID files from previous sessions
2. `cleanup-stale-workflow.py` — clears stale `active-workflow` flags older than the session
3. `detect-ivy-workspace.sh` — auto-detects `.ivyworkspace` markers, writes `IVY_WORKSPACE_ROOT`, `IVY_LSP_LOG_PATH`, `IVY_MCP_LOG_PATH`, `IVY_SESSION_ID`, `IVY_MCP_PID_FILE`, and (conditionally) `IVY_ACTIVE_WORKSPACE` to `CLAUDE_ENV_FILE`
4. `observe.py --event SessionStart` — observability: records session start metadata
5. `wait-for-indexing.sh` — waits up to 20s for the LSP index to be ready before the first tool call; reads env vars exported by step 3

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

Fire after tool execution, before the result is returned to Claude. Hooks are grouped by matcher; within each matcher group they fire in the order listed. See `.claude/rules/postuse-hook-ordering.md` for the ordering contract that governs the `Write|Edit` group.

| Hook | Applies to | Effect |
|------|-----------|--------|
| track-workflow-skill.py | `Skill` invocations | Records phase transitions to the workflow journal |
| auto-load-skill-references.py | `Skill` invocations | Injects relevant reference files into context after skill activation |
| post-write-ivy-lint.sh | `Write` or `Edit` on `.ivy` files | Runs `ivy_diagnostics(mode="structural")` automatically after every Ivy file save |
| post-write-workflow-aware.py | `Write` or `Edit` | Workflow-aware post-write processing (phase tracking, build-state updates) |
| assess-modeling.py | `Write` or `Edit` | Adversarial G2 critic: analyses modeling quality, emits `[GAP: #NN]` markers for model-layer findings |
| assess-testspec.py | `Write` or `Edit` | Adversarial G3 critic: analyses test-spec quality, emits `[GAP: #NN]` markers for testspec-layer findings |
| assess-trace.py | `ivy_iut_test` | Analyses IUT trace after each test run; surfaces assertion failures and unexpected event sequences |
| interaction-checkpoint.py | `ivy_verify`, `ivy_coverage`, `ivy_extract_requirements`, `ivy_quality` | Records interaction checkpoint for session continuity |
| render-tool-result.py | `ivy_verify`, `ivy_coverage`, `ivy_diagnostics`, `ivy_compile`, `ivy_quality` | Reformats raw JSON result to workflow-appropriate prose or tables; style adapts to active overlay |
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
| `raw` | All other MCP tools (ivy_model_info, ivy_analysis, ivy_status, ivy_extract_requirements, ivy_manifest, ivy_rfc, ivy_visualize, ivy_patterns, ivy_propagation, ivy_workspace, ivy_workflow_state, ivy_index, ivy_iut_test) |

## PostToolUseFailure Hooks

Fire after tool execution when the tool itself returns an error (distinct from `PostToolUse`, which fires on success). No matcher — applies to all tools.

| Hook | Applies to | Effect |
|------|-----------|--------|
| observe.py --event PostToolUseFailure | All tools (no matcher) | Observability: records the failed tool call and error metadata to the JSONL session log |

## Notification Hooks

Fire when Claude Code receives a notification event (e.g., MCP server disconnect alert). No matcher. Ordering: `notify-mcp-disconnect.py` fires first so the user sees the alert promptly; `observe.py` records it last so the log captures the full notification.

| Hook | Applies to | Effect |
|------|-----------|--------|
| notify-mcp-disconnect.py | All notifications (no matcher) | Detects MCP-disconnect notifications and surfaces them to the user promptly |
| observe.py --event Notification | All notifications (no matcher) | Observability: records notification event metadata |

## SubagentStart Hooks

Fire when a sub-agent is spawned. No matcher.

| Hook | Applies to | Effect |
|------|-----------|--------|
| observe.py --event SubagentStart | All sub-agent spawns (no matcher) | Observability: records sub-agent start metadata to the JSONL session log |

## SubagentStop Hooks

Fire when a sub-agent terminates. No matcher.

| Hook | Applies to | Effect |
|------|-----------|--------|
| observe.py --event SubagentStop | All sub-agent stops (no matcher) | Observability: records sub-agent stop metadata to the JSONL session log |

## PreCompact Hooks

Fire before Claude Code compacts the conversation context. No matcher.

| Hook | Applies to | Effect |
|------|-----------|--------|
| observe.py --event PreCompact | All compaction events (no matcher) | Observability: records pre-compaction metadata so the session log captures context boundaries |

## PermissionRequest Hooks

Fire when Claude Code surfaces a permission prompt to the user. No matcher.

| Hook | Applies to | Effect |
|------|-----------|--------|
| observe.py --event PermissionRequest | All permission requests (no matcher) | Observability: records permission request metadata to the JSONL session log |

## Stop / SessionEnd Hooks

| Event | Hook | Effect |
|-------|------|--------|
| Stop | record-session-end.py | Finalizes session log entry |
| Stop | render-summary.py | Renders session summary (workflow phases completed, errors encountered) |
| Stop | observe.py --event Stop | Observability: records session end |
| SessionEnd | cleanup-ivy-lsp.sh | Stops the LSP server and cleans up socket/PID files |
| SessionEnd | observe.py --event SessionEnd | Observability: records session end metadata |
