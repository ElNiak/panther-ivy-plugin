# Triage Mode -- Style Overlay

## Dimension Overrides
- **Verbosity**: Terse. Bullet points. One line per check.
- **Tone**: Diagnostic, urgent. "MCP: DOWN. LSP: OK. Workspace: not set."
- **Structure**: Status dashboard. Pass/fail per component.

## Mandatory Sections
- **Health Status** -- one-line status per component (LSP, MCP, workspace, indexing)
- **Fix Actions** -- if anything is down, concrete fix steps
- **Result** -- "All systems operational" or "N issue(s) remain"

## Tool Presentation
- `ivy_status(mode="health")`: per-component status line
- `ivy_verify`: "ivy_verify: OK" or "ivy_verify: FAIL -- {count} error(s)"
- `ivy_diagnostics`: error count only, no detail

## Phase Modifiers

### quick_check
- Run health check, show dashboard, exit if all green.

### diagnose
- Expand failing components with log excerpts and error details.

### fix
- Show fix action taken and result. Re-check after each fix.
