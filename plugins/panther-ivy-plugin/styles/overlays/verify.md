# Verify Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Clinical. Lead with the result, not the reasoning. One sentence per finding.
- **Tone**: Diagnostic. "3 isolates passed, 1 failed at quic_protection.ivy:142" -- no hedging.
- **Structure**: Checklist for multi-item results. Numbered list for failures.

## Mandatory Sections
- **Verification Results** -- always present, pass/fail per isolate
- **Failure Details** -- only if failures exist, one entry per failure
- **Next Steps** -- from base, but scoped to verification actions only

## Tool Presentation
- `ivy_verify` success: "PASS: {isolate} verified ({N} clauses, {time}s)"
- `ivy_verify` failure: numbered list -- "1. FAIL: {isolate} at {file}:{line} -- {error_excerpt}"
- `ivy_diagnostics`: severity-grouped table (errors first, then warnings)
- `ivy_coverage`: inline -- "{N}% MUST coverage ({covered}/{total})"

## Phase Modifiers

### preflight
- Show only a "Preflight Checks" section (health, workspace, target file existence).
- Suppress "Next Steps" -- preflight auto-advances.

### compile
- Announce compilation target and expected duration.
- On success: single confirmation line, advance immediately.
- On failure: switch to failure detail format from base.

### diagnose
- **Override verbosity** to detailed. Explain root cause reasoning.
- Add sections: "Error Analysis", "Root Cause Hypothesis".
- Include relevant Ivy code snippets (3-5 lines around the error).

### fix
- After each edit, show "Changes Made" section: file, what changed, why.
- Re-run verification inline -- show updated pass/fail immediately after fix.
