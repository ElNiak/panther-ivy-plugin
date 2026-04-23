---
category: tier-a-always-on
---

## Ivy Formatting Conventions

- Cite RFC sections as `[rfcNNNN:X.Y]` inline, never as footnotes. Always include
  the complete normative quote from the cited section (all MUST/SHOULD/MAY language).
  Never truncate or paraphrase normative text.
- Format errors as: `ERROR: {file}:{line} -- {message}`.
- Format warnings as: `WARN: {file}:{line} -- {message}`.
- Reference Ivy files with relative paths from protocol-testing root.
- When referencing claims, assertions, or design decisions, quote the source
  verbatim with a bracketed reference.
- Suppress raw JSON from MCP tool results. Render as formatted prose or tables.

## Self-Review

- After producing a model response to the user that contains analysis,
  recommendations, or design choices, append a brief "Considerations" block
  listing:
  - **Pro**: What this approach gets right
  - **Con**: What risks, trade-offs, or limitations exist
  - **Alternatives considered**: Other options and why they were not chosen
- This rule governs Claude's response to the user, not plugin source documents
  (skills, rules, agents) that teach these conventions.
- For simple factual outputs (tool results, file listings), skip self-review.
