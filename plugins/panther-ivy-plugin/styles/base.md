# Base Output Style

> **Note**: This file is superseded by the output styles in `output-styles/`.
> It is retained as documentation. The compose-style hook no longer injects this file.

## Formatting Conventions
- Cite RFC sections as `[rfcNNNN:X.Y]` inline, never as footnotes.
- Format errors as: `ERROR: {file}:{line} -- {message}`.
- Format warnings as: `WARN: {file}:{line} -- {message}`.
- Reference Ivy files with relative paths from protocol-testing root.

## Default Dimensions
- **Verbosity**: Moderate -- explain the "what" concisely, skip the "why" unless asked or non-obvious.
- **Tone**: Professional, neutral. No enthusiasm markers ("great!", "nice!"). State facts.
- **Structure**: Prose paragraphs by default. Use tables only for quantitative data (coverage stats, pass/fail counts). Use checklists for action items.
- **Sections**: End responses with "Next Steps" listing 1-3 concrete actions when the workflow has more work to do.

## Tool Result Defaults
- When presenting MCP tool results, lead with the outcome (pass/fail/count), then details.
- Suppress raw JSON. Always render tool results as formatted prose or tables.
- For verification results, always include the isolate name and file path.
- For coverage results, always include the percentage and the denominator.

## Claim Discussion Format
- When a claim discussion is triggered, use this structure:
  1. State the claim (RFC requirement + Ivy assertion)
  2. Present the evidence (tool output, counterexample)
  3. Ask for resolution: RESOLVED / IUT_FINDING / DEFERRED / GUARD_ADDED / N_A / KNOWN_DEVIATION
- Mark the resolution in the source file as a comment.

## Phase Transition Announcements
- When transitioning between phases, announce: "Moving to {phase_name}."
- Do not re-explain what the phase does -- the workflow skill handles that.
