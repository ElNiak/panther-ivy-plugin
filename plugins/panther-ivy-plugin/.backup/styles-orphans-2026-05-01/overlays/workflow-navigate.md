# Navigate Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Conversational. Provide context for what happened and what's available.
- **Tone**: Welcoming, orienting. "You left off mid-build on the QUIC connection layer."
- **Structure**: Prose with embedded suggestions. No tables unless showing workspace status.

## Mandatory Sections
- **Context Summary** -- where the user left off, active workspace, modified files
- **Available Actions** -- what workflows are available given current state
- **Suggested Next Step** -- one recommended action based on state

## Tool Presentation
- `ivy_status(mode="health")`: prose summary -- "LSP and MCP are healthy. Workspace: quic (client+server)."
- `ivy_workspace get`: inline -- "Active workspace: {protocol} ({roles})"
- Build state (if resuming): layer completion table

## Phase Modifiers

### warm_resume
- Lead with "Resuming previous session." then context summary.
- If build-state.yaml exists, show layer progress table.

### cold_start
- Lead with "Welcome." then workspace detection results.
- Show available protocols and suggest `/set-workspace`.

### activity_summary
- Summarize recent git changes to .ivy files.
- Highlight files with unresolved claim discussions.
