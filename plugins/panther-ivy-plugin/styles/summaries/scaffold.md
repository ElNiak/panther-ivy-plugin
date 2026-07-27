# Scaffold Session Summary

## Sections (in order)

### Layer Progress
Table from build-state.yaml:
| Layer | File | Status |
|-------|------|--------|

### Decisions Made
- List from build-state.yaml decisions array

### Verification Status
- If any layers were verified: show pass/fail per layer
- If scaffold reached Phase 4 (verify): show verification summary

### Next Session
- Next layer in dependency order
- Any blockers or open questions from this session

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
