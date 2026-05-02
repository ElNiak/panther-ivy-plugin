# Refine Session Summary

## Sections (in order)

### Verification Results
- Total isolates attempted: {isolates_attempted}
- Passed: {pass_count} | Failed: {fail_count}
- List each failed isolate: "{isolate} at {file}:{line}"

### Claim Resolutions
- Show counts by type: {resolved} confirmed, {iut_findings} IUT findings, {deferred} deferred
- If any IUT_FINDING: list them with file and RFC section

### Outstanding Work
- List isolates not yet attempted or still failing
- If in diagnose/fix phase at session end: note "Fix in progress for {isolate}"

### Session Metrics
- Tool calls: top 3 by frequency
- Session duration hint (from observability timestamps)

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
