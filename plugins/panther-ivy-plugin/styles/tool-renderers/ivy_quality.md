# ivy_quality -- Result Renderer

## Input Fields
Varies by mode. suggestions: {suggestions (list of {category, message, severity})}. gate: {passed, gate_level, failures}.

## Default
- suggestions: Numbered list by severity.
- gate: "Gate {gate_level}: PASS" or "Gate {gate_level}: FAIL -- {failure_count} issue(s)"

## verify
- suggestions: Suppress unless explicitly requested.
- gate: Inline pass/fail.

## build
- suggestions: Show suggestions relevant to current layer.
- gate: Show gate result with per-criterion breakdown.

## review
- suggestions: Full numbered list grouped by category.
- gate: Detailed table: | Criterion | Status | Details |

## triage
- suggestions: Suppress.
- gate: "Quality gate: PASS" or "Quality gate: FAIL ({failure_count})"
