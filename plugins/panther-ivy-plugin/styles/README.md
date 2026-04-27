# styles/

Plugin-internal rendering assets composed at runtime by hooks. **Not** user-facing
output styles — for those, see the sibling `output-styles/` directory.

## Subdirectories

| Subdir            | Consumer hook                                | Role |
|-------------------|----------------------------------------------|------|
| `overlays/`       | `hooks/scripts/compose-style.py` (UserPromptSubmit) | Per-workflow style overlays layered on top of the user's selected output style. One file per workflow (build, verify, review, triage, navigate). |
| `summaries/`      | `hooks/scripts/render-summary.py` (Stop)     | Per-workflow summary templates rendered at session end from the workflow journal. One file per workflow. |
| `tool-renderers/` | `hooks/scripts/render-tool-result.py` (PostToolUse) | Per-tool result formatters (one file per `mcp__plugin_panther-ivy-plugin_ivy-tools__*` tool that produces structured output). Converts raw JSON tool results into formatted prose or tables. |

## Why split from output-styles/

The harness owns the user-facing output style namespace; the plugin owns its
own internal rendering assets. Mixing them would conflate two ownership models:

- `output-styles/*.md` are loaded by the harness style picker and become part of
  the system prompt for the whole session.
- `styles/**/*.md` are loaded by the plugin's hooks at specific events; they do
  not enter the system prompt, only `additionalContext` for the relevant tool
  call or summary.

Future contributors must not consolidate the two directories; the split is a
deliberate ownership boundary.

## Adding a new overlay/summary/renderer

1. Drop the markdown file under the appropriate subdirectory using the existing
   per-workflow or per-tool naming convention.
2. The consumer hook discovers it on the next session (no `hooks.json` edit
   needed for the standard naming pattern).
3. Add a row to the table above so the new file is discoverable.
