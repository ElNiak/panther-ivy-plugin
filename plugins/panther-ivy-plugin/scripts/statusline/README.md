# panther-ivy-plugin statusline

Specialized Claude Code status bar for the Ivy formal protocol testing plugin.
Renders five plugin-specific segments (protocol, workflow, LSP, MCP, test file)
alongside your existing global statusline. Outside an Ivy workspace, it
delegates to the user's global script unchanged.

## User setup

Add the following to `~/.claude/settings.json` (or whichever settings file
Claude Code loads first):

```json
"statusLine": {
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/scripts/statusline/main.sh"
}
```

That is the only required step. Hooks already fire on the events that change
plugin state — they populate the statusline cache automatically.

## Modes

Set via `PANTHER_IVY_STATUSLINE_MODE` or the `statusline_mode` plugin
user-config value. Precedence: env var > user-config > built-in default
(`suppress-overlaps`).

| Mode | What appears before the Ivy segments |
|---|---|
| `ivy-only` | nothing — Ivy segments only |
| `minimal` | git branch, model, context% |
| `full-delegate` | full output of the global statusline |
| `suppress-overlaps` *(default)* | global output without `dir` (since `protocol` replaces it) |

## Segments

In rendering order, separated by ` · ` (middle dot):

| Segment | Format | States |
|---|---|---|
| `protocol` | `🐍 bgp` | always present in-workspace |
| `workflow` | `wf:refine:compile` | `wf:—` when none |
| `lsp` | `lsp:ready` / `lsp:idx 12/40` / `lsp:starting` / `lsp:down` | green / yellow / red; dim `?` if cache > 60s old |
| `mcp` | `mcp:up 34ms` / `mcp:degraded` / `mcp:down ⚠` | green / yellow / red; dim `?` if cache > 60s old |
| `testfile` | `test:frr_open.ivy` | hidden when no test file is tracked |

Stale cache (mcp/lsp older than 60 s) dims the segment and appends `?`.
If the global statusline subprocess timed out, the marker becomes `!` to
distinguish that failure mode from cache staleness.

## Environment variables

| Variable | Purpose |
|---|---|
| `PANTHER_IVY_STATUSLINE_MODE` | override mode for this session |
| `PANTHER_IVY_STATUSLINE_DEBUG=1` | log render errors to `~/.claude/panther-ivy-plugin/logs/statusline.log` (rotates at 1 MB) |
| `PANTHER_IVY_GLOBAL_STATUSLINE` | path to the global script (default `~/.claude/statusline-command.sh`) |
| `PANTHER_IVY_STATUSLINE_GLOBAL_TIMEOUT` | seconds to wait for the global subprocess (default `1`) — bump if your global script runs git, cost accounting, or other sub-commands that occasionally exceed it |
| `PANTHER_IVY_STATUSLINE_CACHE_PATH` | *(tests only)* override the cache file path |
| `PANTHER_IVY_STATUSLINE_CACHE_ROOT` | *(tests only)* override the cache directory root |
| `PANTHER_IVY_STATUSLINE_STALE_SECONDS` | *(tests only)* override the 60 s stale threshold |
| `CLAUDE_STATUSLINE_COLORS` | inherited from global — set to `false` to disable ANSI colors |
| `CLAUDE_STATUSLINE_EMOJIS` | inherited from global — set to `false` to disable emoji markers |
| `NO_COLOR` | standard env var; also disables colors |

## Cache

Hooks maintain `~/.claude/panther-ivy-plugin/cache/<sha1-of-workspace-root-12>/statusline.json`.
The statusline only reads this file — it never probes live state.

Writers:

| Hook | Section |
|---|---|
| `workspace/detect.py` (SessionStart) | `workspace`, initial `mcp` |
| `mcp/indexing-wait.py` (SessionStart) | `mcp`, `lsp` |
| `mcp/indexing-ready.py` (PreToolUse mcp_*ivy) | `lsp` |
| `mcp/health.py` (PreToolUse mcp_*ivy) | `mcp` |
| `mcp/disconnect-notify.py` (Notification) | `mcp.status = "down"` |
| `record/skill-invocation.py` (PostToolUse Skill) | `active_skill` |
| `render/workflow-aware-annotation.py` (PostToolUse Write/Edit/Agent) | `test_file`, `active_agent` |

All writes go through `hooks/scripts/statusline_cache.py`. Each write does an
atomic tempfile + `os.replace`; concurrent writers across hooks serialize
on a sibling `statusline.json.lock` file held `fcntl.LOCK_EX` for the full
read-modify-write, so two simultaneous hooks touching different sections
cannot silently overwrite each other.

## Debugging

1. `cat ~/.claude/panther-ivy-plugin/cache/*/statusline.json` to see the raw cache.
2. `PANTHER_IVY_STATUSLINE_DEBUG=1 bash scripts/statusline/main.sh <<< '{"workspace":{"current_dir":"<your-workspace>"}}'` to render once with logging.
3. `~/.claude/panther-ivy-plugin/logs/statusline.log` captures errors when debug is enabled.

## File layout

```
scripts/statusline/
├── main.sh                   # entry point (invoked by Claude Code)
├── cache.sh                  # sourced: cache reader helpers
├── colors.sh                 # sourced: ANSI constants
├── workspace.sh              # sourced: workspace detection
├── segments/
│   ├── protocol.sh
│   ├── workflow.sh
│   ├── lsp.sh
│   ├── mcp.sh
│   └── testfile.sh
└── README.md                 # you are here
```
