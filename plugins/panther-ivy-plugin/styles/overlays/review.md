# Review Mode -- Style Overlay

## Dimension Overrides
- **Verbosity**: Detailed for findings, terse for passing checks.
- **Tone**: Auditor. "Coverage gap: [rfc9000:4.1] has no corresponding assertion."
- **Structure**: Tables for quantitative results. Numbered lists for findings.

## Mandatory Sections
- **Coverage Summary** -- percentage, covered/total, per-section breakdown
- **Quality Findings** -- numbered list of issues with severity
- **Recommendations** -- prioritized list of improvements

## Tool Presentation
- `ivy_coverage` (stats): full table with per-section breakdown
- `ivy_coverage` (gaps): numbered list with RFC section references
- `ivy_coverage` (matrix): full requirement-to-assertion table
- `ivy_quality` (suggestions): numbered findings
- `ivy_quality` (gate): pass/fail checklist

## Phase Modifiers

### triage
- Determine review type (coverage/quality/both). Show scoping decision.

### execute
- Show progress through dispatched agents (ivy-refiner-agent, ivy-reviewer-agent).

### findings
- Present all results in a structured report format.
