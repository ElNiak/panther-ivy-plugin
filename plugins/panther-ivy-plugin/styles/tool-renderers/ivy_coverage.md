# ivy_coverage -- Result Renderer

## Input Fields
Varies by mode. stats: {covered, total, percentage, by_section}. gaps: {uncovered_requirements, unguarded_state}. matrix: {requirement_to_assertion_map}.

## Default
- stats: "{percentage}% MUST coverage ({covered}/{total})"
- gaps: Bullet list of uncovered requirements
- matrix: Table with requirement -> assertion mapping

## verify
- stats: Inline -- "{percentage}% ({covered}/{total})" -- no table.
- gaps: Suppress unless explicitly requested.

## build
- stats: Show per-layer breakdown if available.
- gaps: Highlight gaps in the layer currently being built.

## review
- stats: Full table with per-section breakdown: | Section | Covered | Total | % |
- gaps: Numbered list with RFC section references.
- matrix: Full table -- this is the primary review artifact.

## triage
- stats: Single line -- "Coverage: {percentage}%"
- gaps/matrix: Suppress.
