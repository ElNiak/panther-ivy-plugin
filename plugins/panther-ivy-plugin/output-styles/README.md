# output-styles/

User-facing output style files exposed to the harness style picker. Each file
in this directory is a top-level posture for a whole session; the user selects
one via `/output-style` (or the equivalent setting). The file's frontmatter
declares the style's identity; the body sets verbosity, tone, structure, and
self-review rules.

| File              | Posture |
|-------------------|---------|
| `ivy-default.md`  | Concise execution mode. Minimal narration, terse status updates, no automatic self-review. |
| `ivy-audit.md`    | Critic mode. Always emits the Considerations block, encourages adversarial framing, suppresses unnecessary action. |
| `ivy-guided.md`   | Collaborative mentor mode. Detailed reasoning, presents 2–3 options at each decision point, ends with a `Next Steps` block via `AskUserQuestion`. |

## Not to be confused with

`styles/` (sibling directory) holds **plugin-internal rendering assets** that
hooks compose at runtime — not user-facing output styles. See `styles/README.md`
for that side of the split. The two directories must not be merged: this one
is consumed by the harness; the other is consumed by the plugin's own hooks.

## How a style takes effect

1. User selects an output style via the harness.
2. The harness exposes the style's body as the active session output style.
3. The plugin's `hooks/scripts/compose-style.py` (UserPromptSubmit hook) layers
   workflow-specific overlays from `styles/overlays/<workflow>.md` on top of
   the user's chosen style and injects the result via `additionalContext`.
4. The `.claude/rules/output-style.md` rule (auto-loaded on `**/skills/*/SKILL.md`
   reads) reminds the agent to honour both the base style and the overlay.
