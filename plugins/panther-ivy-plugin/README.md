# panther-ivy-plugin — Ivy Formal Protocol Testing

> **Developer reference.** This README is for contributors reading the source; it is not auto-loaded by Claude Code. Runtime content lives in `skills/*/SKILL.md`, `.claude-plugin/plugin.json`, and `.claude/rules/*.md` — all auto-discovered. The agent-facing "Specification Engineer" framing lives canonically in `skills/ivy/SKILL.md` (the orchestrator skill).

Provides Ivy LSP (diagnostics, navigation), MCP tools (verification, compilation, analysis), specialist agents, gate-critic agents, and skills.

## Layout (post-F.1, v0.11.0)

| Component | Count | Location |
|---|---|---|
| Orchestrator skill (single entry point) | 1 | `skills/ivy/` |
| Workflow ops-skills (preloaded by specialist agents) | 5 | `skills/{triage,build,verify,review,meta-self-mod}-ops/` |
| Cross-cutting knowledge skills (thin SKILL.md + on-demand `references/`) | 7 | `skills/{ivy-toolkit,ivy-syntax,methodology,verification-failures,specification-patterns,propagation-patterns,apt-attack-patterns}/` |
| Maintainer self-audit skill | 1 | `skills/reference-drift/` |
| Workflow specialist agents | 5 | `agents/ivy-{triage,builder,verifier,reviewer,meta}-agent.md` |
| Gate-critic agents | 3 | `agents/g-{plan,fidelity,knowledge}-critic.md` |
| Hook scripts | 24 distinct (35 registrations across 12 events) | `hooks/scripts/` |
| Slash commands | 2 | `commands/{nct-iut-test,nct-health}.md` |
| Output style | 1 | `output-styles/ivy-guided.md` |
| `.claude/rules/` files | 15 | `.claude/rules/*.md` |

## Workflow Routing

Runtime routing lives in the orchestrator skill at `skills/ivy/SKILL.md`. The orchestrator is the single entry point: every panther-ivy-plugin session loads it first, and it routes to one of the five specialist agents (verifier, builder, reviewer, triage, meta) or reads its own `references/` for knowledge questions. There is no `routing-rules.json` and no `route-user-prompt.py` hook anymore; activation is driven by the orchestrator's description matching the user's request.

### Routing Rules
1. If a workflow is already active (check `<protocol-directory>/.panther-ivy/active-workflow`), stay in it unless the user explicitly asks to switch.
2. Direct tool requests ("call ivy_verify on X") use shortcut commands, not workflows.
3. Learning questions ("how does NCT work?") are answered using loaded knowledge skills, no workflow activation.
4. Every workflow returns to the orchestrator on completion.

## G6 UX cost

The G6 knowledge-capture gate dispatches inline on **cold-start-eligible session-resume turns** after Ivy activity. Dispatch cost: 3 Sonnet-tier critics × ~90s wall-clock = ~90s blocking before Phase 1.5 yields control.

PROJECT.md warm-resume turns and `pending_dispatch` warm-resume turns do **NOT** pay this cost — G6 sits after both warm-resume branches and only fires when Phase 1.5 would otherwise drop to cold-start.

Power users can opt out for the current session by setting `IVY_DISPATCH_G6=0` in their shell environment before invoking Claude Code. The skip path emits `[ivy-noop] G6 skipped (env opt-out)`; no `gate_dispatched{gate=g6}` is written.

## State Management

Read `.panther-ivy/active-workflow` on every turn to know your current workflow phase.

**Active-workflow flag** (`<protocol-dir>/.panther-ivy/active-workflow`):
```yaml
workflow: verify
phase: compile
started: "2026-04-28T14:30:00Z"
```

**Scaffold-state file** (`<protocol-dir>/.panther-ivy/scaffold-state.yaml`): Multi-session scaffold progress. Written by the builder agent at Phase 2. Read by the orchestrator for warm session resume.

**Workflow composition:** Workflows compose via `pending_dispatch` journal events on the orchestrator (`skills/ivy/SKILL.md`), not via a caller chain. When a workflow needs another workflow to run next (e.g., build → verify after Phase 4), it appends `pending_dispatch(target_workflow=<next>, reason=<why>)` and clears its own active-workflow flag. The orchestrator's Phase 1 Step 2c consumes the event on the next turn (or same-turn if the harness routes in-line), writes a paired `workflow_resumed` marker for idempotency, and dispatches the target.

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

The orchestrator (`skills/ivy/SKILL.md`) is the single user-facing entry point. It routes natural-language requests to one of six specialist agents, each preloaded with its matching ops-skill:

| Specialist agent | Ops-skill | Purpose |
|---|---|---|
| `ivy-builder-agent` | `scaffold-ops` | Construct or extend protocol models (NCT/NACT/NSCT) |
| `ivy-refiner-agent` | `refine-ops` | Run `ivy_verify` / `ivy_compile`, dispatch G4 inline, diagnose counterexamples, drive Phase 7 fix loop |
| `ivy-experimenter-agent` | `experiment-ops` | Configure + run IUT experiments, dispatch G5 inline, apply 9-step trace analysis |
| `ivy-reviewer-agent` | `review-ops` | RFC coverage audit, quality scoring, traceability |
| `ivy-triage-agent` | `triage-ops` | MCP/LSP/Serena health repair, 9-step diagnostic runbook |
| `ivy-meta-agent` | `meta-self-mod-ops` | Plugin source modifications (skills, agents, hooks, rules, commands) |

### Shortcut Commands

Direct tool access (bypass orchestrator):

- `/nct-iut-test <protocol> <test> <iut>` — runs an IUT test via `panther run`
- `/nct-health` — 9-step MCP/LSP diagnostic runbook

### Internal Components

**Specialist agents** (dispatched by the orchestrator) — see the Available Workflows table above.

**Gate-critic agents** (dispatched at adversarial quality gates, not user-facing):
`g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`.

**Knowledge skills** (loaded by workflows, not user-facing):
`verification-failures`, `specification-patterns`, `propagation-patterns`, `apt-attack-patterns`, `ivy-syntax`, `ivy-toolkit`, `methodology`.

Knowledge capture (review session learnings, audit plugin skills/references) is now handled by the orchestrator's G6 Knowledge Gate (see `skills/ivy/SKILL.md`), which dispatches `g-knowledge-critic`. There is no separate user-invocable knowledge-capture skill.

## Workspace Awareness

The plugin supports active workspace scoping to prevent cross-protocol collisions in Ivy formal models.

### Management

Workspace management is exclusively via the `ivy_workspace` MCP tool (the table below documents its actions). The previous `/set-workspace` and `/clear-workspace` slash commands were removed in Phase E of the orchestrator refactor; use the MCP tool instead.

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
- Calling `ivy_workspace(action='clear')` removes all restrictions

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

Output formatting is a 2-layer stack:

1. **Shared rules** (`.claude/rules/ivy-formatting.md`) — citation format, error format,
   self-review. Always loaded. Also loaded by subagents via CLAUDE.md inheritance.
2. **Output style** (`output-styles/ivy-guided.md`) — dimension defaults (verbosity, tone, structure).
   User-selected at session level. NOT inherited by subagents.

Tool result formatting is handled programmatically by `render/tool-result.py`
(PostToolUse hook). Do not duplicate tool formatting rules in the output style.

Two subdirectories of `styles/` carry per-artifact templates consumed by the hooks:

- `styles/tool-renderers/` — one file per rendered MCP tool (e.g. `ivy_verify.md`, `ivy_coverage.md`). Each file specifies the output phrasing per workflow / phase; `render/tool-result.py` selects the right section at runtime.
- `styles/summaries/` — one summary template per workflow, loaded by `render/summary/main.py` (Stop hook) to produce the end-of-session recap.

Neither directory is user-facing; changes there propagate through hooks only.

A third subdirectory, `styles/overlays/`, contains workflow-overlay templates referenced by `hooks/scripts/style_utils.py` but no longer wired into any kept hook (Phase D archived the overlay-consumer logic from `prompt/style.py`, the prior consumer). It is legacy infrastructure pending cleanup; runtime behaviour is unaffected.

### Style Precedence Rules

- Skills that define fixed output formats (the `verification-failures`
  resolution-comment prefixes and counterexample trace format, finding IDs)
  override the output style's structure dimension for those specific artifacts.
  The style applies to surrounding prose, not to structured artifacts with
  fixed schemas.
- Memory and persistence artifacts (scaffold-state.yaml, session logs, workflow
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

These are written to `$CLAUDE_ENV_FILE` by `workspace/detect.py` so downstream hooks and the MCP / LSP server processes inherit them. Do not set them manually.

| Variable | Purpose |
|---|---|
| `IVY_WORKSPACE_ROOT` | Absolute path to the detected Ivy workspace root |
| `IVY_SESSION_ID` | Date-prefixed Claude session id used for per-session log and cache directories |
| `IVY_LSP_LOG_PATH` | Path to the latest LSP log symlink |
| `IVY_MCP_LOG_PATH` | Path to the latest MCP log symlink |
| `IVY_MCP_PID_FILE` | PID file path for the MCP server |
| `IVY_ACTIVE_WORKSPACE` | Workspace group name when one is explicitly set via `ivy_workspace(action='set')` |

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

**Orchestrator**: `skills/ivy/SKILL.md` — single entry point; routes to specialist agents.
**Specialist agents**: ivy-builder-agent, ivy-refiner-agent, ivy-experimenter-agent, ivy-reviewer-agent, ivy-triage-agent, ivy-meta-agent.
**Gate-critic agents**: g-plan-critic, g-fidelity-critic, g-knowledge-critic.
**Shortcuts**: /nct-iut-test, /nct-health.
**Cross-cutting knowledge skills**: verification-failures, specification-patterns, propagation-patterns, apt-attack-patterns, ivy-syntax, ivy-toolkit, methodology.
