# ivy_diagnostics -- Result Renderer

## Input Fields
Returns: issues (list of {file, line, severity, message, layer}), summary counts.

## Default
- Severity-grouped list: errors first, then warnings.
- Include file:line for each.

## verify
- Severity-grouped table: | Severity | File | Line | Message |
- Errors first, warnings second.

## build
- Filter to current layer only.
- Show as numbered list with fix suggestions.

## review
- Full table with layer column: | Layer | Severity | File | Line | Message |
- Include summary counts at top.

## triage
- Count only: "{error_count} errors, {warning_count} warnings"
- Detail suppressed unless in diagnose phase.
