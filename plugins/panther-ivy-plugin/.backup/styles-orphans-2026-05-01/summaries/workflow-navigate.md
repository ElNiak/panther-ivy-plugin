# Navigate Session Summary

## Sections (in order)

### Session Activity
- Files modified (from git diff)
- Workflows activated during session (from observability)

### Workspace State
- Active workspace at session end
- Build state summary if build-state.yaml exists

### Claim Resolutions
- Show counts by type: {resolved} confirmed, {iut_findings} IUT findings, {deferred} deferred

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
