# panther-ivy-plugin — Ivy Formal Protocol Testing

> **Developer reference.** This README documents the plugin's architecture, routing, tools, and conventions for contributors reading the source. It is **not** auto-loaded into Claude Code at plugin install time — Claude Code's plugin auto-discovery targets `.claude-plugin/plugin.json`, `commands/`, `agents/`, `skills/`, `hooks/`, `.mcp.json`, `scripts/`, not README.md. Load-bearing runtime content lives in `skills/*/SKILL.md` and `.claude/rules/*.md`, which **are** auto-discovered. The agent-facing "Specification Engineer" framing that used to appear in this README now lives canonically in `skills/navigate/SKILL.md` so it actually reaches the agent at runtime; see that file for the current wording.

Provides Ivy LSP (diagnostics, navigation), MCP tools (verification, compilation, analysis), agents, and skills.

## Workflow Routing

Runtime routing is driven by `routing-rules.json`, which is authoritative: it defines the keyword, regex, file-trigger, and priority entries the `route-user-prompt.py` hook consults on every `UserPromptSubmit`. The five user-facing workflows (`verify`, `build`, `review`, `triage`, `navigate`) and one learning-injection bucket are declared there; refer to that file directly for the matching vocabulary, do not maintain a parallel table here.

### Routing Rules
1. If a workflow is already active (check `<protocol-directory>/.panther-ivy/active-workflow`), stay in it unless the user explicitly asks to switch.
2. Direct tool requests ("call ivy_verify on X") use shortcut commands, not workflows.
3. Learning questions ("how does NCT work?") are answered using loaded knowledge skills, no workflow activation.
4. Every workflow returns to navigate on completion.

## State Management

Read `.panther-ivy/active-workflow` on every turn to know your current workflow phase.

**Active-workflow flag** (`<protocol-dir>/.panther-ivy/active-workflow`):
```yaml
workflow: verify
phase: compile
started: "2026-04-07T14:30:00Z"
```

**Build-state file** (`<protocol-dir>/.panther-ivy/build-state.yaml`): Multi-session build progress. Written by the build workflow at Phase 2. Read by navigate for warm session resume.

**Workflow composition:** Workflows compose via `pending_dispatch` journal events, not via a caller chain. When a workflow needs another workflow to run next (e.g., build → verify after Phase 4), it appends `pending_dispatch(target_workflow=<next>, reason=<why>)` and clears its own active-workflow flag. Navigate's Phase 1 Step 2c consumes the event on the next turn (or same-turn if the harness routes in-line), writes a paired `workflow_resumed` marker for idempotency, and dispatches the target.

## Tool Rules — CRITICAL

**CLI commands with MCP equivalents** — a PreToolUse hook warns when these are used directly. Prefer MCP tools for structured output:

| Warned CLI | Required MCP Tool | Purpose |
|---|---|---|
| `ivy_check` | `ivy_verify` | Formal verification (isolates, invariants, safety) |
| `ivyc` | `ivy_compile` | Compile test executable (`target=test`) |
| `ivy_show` | `ivy_model_info` | Model introspection (types, relations, actions) |
| `ivy_to_cpp` | `ivy_compile` | C++ code generation |

**Verification & compilation**: ivy_verify, ivy_compile, ivy_model_info
**Analysis & diagnostics**: ivy_diagnostics (modes: structural/full/dashboard), ivy_analysis (modes: includes/scope)
**Workflow & workspace**: ivy_workspace, ivy_workflow_state, ivy_status (modes: health/capabilities), ivy_index
**Coverage & traceability**: ivy_coverage (stats/gaps/matrix), ivy_extract_requirements, ivy_manifest
**RFC lookup**: ivy_rfc (mode: get/search/section)
**Visualization**: ivy_visualize (views: dependencies/state_machine/layers/summary/requirements)
**Quality & patterns**: ivy_quality, ivy_patterns (modes: analyze/validate/compare/check/scaffold)
**Propagation**: ivy_propagation (modes: variants/serdes/impact)
**Testing**: ivy_iut_test

For parameters, timeouts, error handling, and rendering details, see the **ivy-toolkit** skill.

**LSP policy (scoped access):** Do not call the `LSP` tool directly for everyday navigation — use `Read`/`Grep`/`Glob` and MCP tools (`ivy_model_info`, `ivy_diagnostics`). Direct LSP calls (`hover`, `goToDefinition`, `findReferences`, `documentSymbol`) are permitted when dispatched by workflow skills. See the `ivy-toolkit` skill for invocation patterns.

**Note**: The LSP server pushes structural diagnostics on file edits. The PostToolUse hook runs `ivy_diagnostics(mode="structural")` automatically after `.ivy` file writes.

**Claude native tools**: `Read`/`Grep`/`Glob` for navigation, `Edit`/`Write` for modification.

### Available Workflows

**User-facing entry points** (activated by routing or natural language):
`navigate`, `verify`, `build`, `review`, `triage`

### Shortcut Commands

**Direct tool access** (bypass workflows):
`/nct-check` (ivy_verify), `/nct-compile` (ivy_compile), `/nct-model-info` (ivy_model_info), `/nct-iut-test` (ivy_iut_test), `/nct-health` (9-step diagnostic), `/nct-observability` (JSONL logs)

### Internal Components

**Agents** (dispatched by workflows, not user-facing):
`spec-analyst`, `model-reviewer`, `traceability-agent`

**Knowledge skills** (loaded by workflows, not user-facing):
`counterexample-guide`, `specification-patterns`, `propagation-patterns`, `apt-attack-patterns`, `ivy-writing-guide`, `ivy-toolkit`, `claim-discussion`, `methodology-reference`, `ivy-debugging-methodology`, `ivy-error-patterns`, `reflection-patterns`

**User-invocable skills** (triggered by user intent or natural-language phrases, not workflow dispatch):
`knowledge-capture` — review session learnings and audit plugin skills/references; also loaded by workflow knowledge gates and `/nct-learn` (`user-invocable: true`)

## Workspace Awareness

The plugin supports active workspace scoping to prevent cross-protocol collisions in Ivy formal models.

### Commands
- `/set-workspace <protocol>` — activate workspace (e.g., `/set-workspace quic`, `/set-workspace apt`)
- `/set-workspace <protocol> <roles>` — activate with role filter (e.g., `/set-workspace quic client+server`)
- `/clear-workspace` — remove workspace restrictions
- `/set-workspace` (no args) — show current workspace and available groups

### How It Works
- **Edit isolation**: When a workspace is active, writes to `.ivy` files outside the active protocol are **blocked** by a PreToolUse hook
- **Include resolution**: The LSP resolver only searches within active layers + stdlib (`ivy/include/1.7`)
- **Auto-restore**: Previous session's workspace is restored on session start with a notice
- **Auto-detection**: Per-protocol `.ivyworkspace` markers auto-scope when opening protocol files
- **Progressive narrowing**: Without explicit workspace, the system suggests scoping after cross-protocol edits

### Scoping Rules
- All MCP tool `relative_path` and `test_file` parameters are workspace-relative
- Use `test_file` parameter for NCT-aligned coverage scoping
- Reads across protocols are always allowed (only writes are constrained)
- Stdlib files (`ivy/include/1.7/`) are always accessible regardless of workspace
- Setting `/clear-workspace` removes all restrictions

### Available Workspaces
`quic`, `apt`, `apt_quic`, `minip`, `bgp`, `coap`, `scaffolds`

### MCP Tool
`ivy_workspace` — programmatic workspace management:
| Action | Parameters | Purpose |
|--------|-----------|---------|
| `set` | `target`, optional `roles` | Activate a workspace |
| `get` | — | Show current workspace state |
| `list` | — | Show available workspace groups |
| `clear` | — | Remove workspace restrictions |

## Style System

Output formatting is a 3-layer stack. Each layer overrides the one below it:

1. **Shared rules** (`.claude/rules/ivy-formatting.md`) -- citation format, error format,
   self-review. Always loaded. Also loaded by subagents via CLAUDE.md inheritance.
2. **Output style** (`output-styles/`) -- dimension defaults (verbosity, tone, structure).
   User-selected at session level. NOT inherited by subagents.
3. **Workflow overlay** (`styles/overlays/`) -- per-workflow and per-phase dimension
   overrides. Injected by `compose-style.py` hook on each user prompt.

Tool result formatting is handled programmatically by `render-tool-result.py`
(PostToolUse hook). Do not duplicate tool formatting rules in output styles or overlays.

Two subdirectories of `styles/` carry per-artifact templates consumed by the hooks:

- `styles/tool-renderers/` — one file per rendered MCP tool (`ivy_verify.md`, `ivy_coverage.md`, `ivy_diagnostics.md`, `ivy_compile.md`, `ivy_quality.md`, `ivy_verdict.md`). Each file specifies the output phrasing per workflow / phase; `render-tool-result.py` selects the right section at runtime.
- `styles/summaries/` — one file per workflow (`build.md`, `navigate.md`, `review.md`, `triage.md`, `verify.md`). These are summary templates loaded by `render-summary.py` (Stop hook) to produce the end-of-session recap.

Neither directory is user-facing; changes there propagate through hooks only.

### Style Precedence Rules

- Workflow overlays override output style dimensions for the active phase.
- Skills that define fixed output formats (claim-discussion resolution comments,
  counterexample-guide trace format, finding IDs) override the output style's
  structure dimension for those specific artifacts. The style applies to
  surrounding prose, not to structured artifacts with fixed schemas.
- Memory and persistence artifacts (build-state.yaml, session logs, workflow
  journal, knowledge-capture entries) are never styled. They use the shared
  rules citation format but not style dimensions.
- Agents do not inherit output styles. They inherit shared rules via CLAUDE.md
  and carry their own output format sections.

## Status Bar

The plugin ships a specialized Claude Code status bar at
`scripts/statusline/main.sh`. When invoked inside an Ivy workspace it renders
protocol, active workflow phase, LSP health, MCP health, and the active test
file alongside the user's global statusline output. Outside a workspace it
execs `~/.claude/statusline-command.sh` unchanged.

Enable it by adding to `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/statusline/main.sh"
}
```

Configure via plugin user-config or env var:
- `statusline_mode` / `PANTHER_IVY_STATUSLINE_MODE`: `ivy-only | minimal | full-delegate | suppress-overlaps` (default)
- `statusline_debug` / `PANTHER_IVY_STATUSLINE_DEBUG=1`: log render errors

Rendering is cache-driven; the existing SessionStart, PreToolUse, PostToolUse,
and Notification hooks populate `~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json`
so the renderer never probes live state. See `scripts/statusline/README.md`.

## Environment Variables

Most settings are configured through Claude Code's `userConfig` (see `plugin.json`) and surfaced as environment variables via `settings.json`. A few internal variables are set at runtime by the SessionStart hooks and consumed by later hooks and the MCP servers.

### User-configurable (via `userConfig`)

| Variable | userConfig field | Default | Purpose |
|---|---|---|---|
| `IVY_LSP_LOG_LEVEL` | `log_level` | `INFO` | LSP / MCP log verbosity (`DEBUG` / `INFO` / `WARN` / `ERROR`) |
| `PANTHER_IVY_ENABLE_SERENA` | `enable_serena` | `0` | Launch the Serena MCP server (requires the `panther-serena` submodule) |
| `IVY_LSP_FORCE_REINSTALL` | `force_reinstall` | `0` | Force `uvx` to reinstall `ivy-lsp` on every server start (useful during local `ivy-lsp` development) |
| `IVY_OBSERVABILITY_ENABLED` | `observability_enabled` | `1` | Emit JSONL observability events to the session log |
| `PANTHER_IVY_STATUSLINE_MODE` | `statusline_mode` | `suppress-overlaps` | Statusline composition: `ivy-only` / `minimal` / `full-delegate` / `suppress-overlaps` |
| `PANTHER_IVY_STATUSLINE_DEBUG` | `statusline_debug` | `0` | Log statusline render errors to `~/.claude/panther-ivy-plugin/logs/statusline.log` |

### Runtime-set (populated by SessionStart hooks)

These are written to `$CLAUDE_ENV_FILE` by `detect-ivy-workspace.sh` so downstream hooks and the MCP / LSP server processes inherit them. Do not set them manually.

| Variable | Purpose |
|---|---|
| `IVY_WORKSPACE_ROOT` | Absolute path to the detected Ivy workspace root |
| `IVY_SESSION_ID` | Date-prefixed Claude session id used for per-session log and cache directories |
| `IVY_LSP_LOG_PATH` | Path to the latest LSP log symlink |
| `IVY_MCP_LOG_PATH` | Path to the latest MCP log symlink |
| `IVY_MCP_PID_FILE` | PID file path for the MCP server |
| `IVY_ACTIVE_WORKSPACE` | Workspace group name when one is explicitly set via `/set-workspace` |

### Optional overrides (user environment)

Set these in your shell environment before starting Claude Code if you need to override the defaults.

| Variable | Default | Purpose |
|---|---|---|
| `IVY_OBSERVABILITY_DIR` | `$IVY_WORKSPACE_ROOT/.observability` then `/tmp/ivy-observability` | Override for JSONL observability log root |
| `IVY_LSP_LOG_DIR` | `/tmp` | Override for LSP / MCP / Serena log directory |
| `IVY_LSP_INCLUDE_PATHS` | `protocol-testing` | LSP indexing include paths (inside a PANTHER workspace without `.ivyworkspace`) |
| `IVY_LSP_EXCLUDE_PATHS` | `submodules,test,doc,examples,notebooks,patches,ivy` | LSP indexing exclude paths |

### Harness-provided

| Variable | Purpose |
|---|---|
| `CLAUDE_PLUGIN_ROOT` | Plugin install directory, used in `hooks.json`, `.mcp.json`, and `settings.json` for path resolution |
| `CLAUDE_ENV_FILE` | Path the harness reads after each hook run to propagate exported env vars to later tool calls |
| `CLAUDE_SESSION_ID` / `CLAUDE_CODE_SESSION_ID` | Claude Code session identifier (consumed by the session-id resolution chain in `hook_utils.resolve_session_id`) |

## Quick Reference

**Workflows**: navigate, verify, build, review, triage
**Shortcuts**: /nct-check, /nct-compile, /nct-model-info, /nct-iut-test, /nct-health, /nct-observability, /nct-learn
**Internal agents**: spec-analyst, model-reviewer, traceability-agent
**Internal knowledge**: counterexample-guide, specification-patterns, propagation-patterns, apt-attack-patterns, ivy-writing-guide, ivy-toolkit, claim-discussion, methodology-reference, ivy-debugging-methodology, ivy-error-patterns, reflection-patterns, knowledge-capture
