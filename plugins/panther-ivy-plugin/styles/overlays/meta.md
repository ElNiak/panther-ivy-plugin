# Meta Mode -- Style Overlay

## Dimension Overrides

These override the user's default brevity preferences when the meta workflow
(plugin self-modification: skills, agents, hooks, .claude/rules, commands,
output-styles, plugin.json) is active.

- **Verbosity**: Detailed. Plugin self-modifications need explicit reasoning so
  future maintainers understand the intent.
- **Thinking style**: Audit-mode. Before edits, surface the conventions being
  followed (e.g., feedback_autoload_rule_no_pointer_stub); after edits, run
  reference-drift checks via Skill(panther-ivy-plugin:reference-drift).
- **Tone**: Methodical.
- **Structure**: State the convention or rule the change preserves, the file(s)
  touched, and any cross-reference impact (other skills, agents, hooks).

## Behavioral Rules

- Before editing plugin source files, invoke `Skill(panther-ivy-plugin:meta-self-mod-ops)`
  to load the operating procedure.
- After every plugin edit, run the plugin test suite from worktree root.
- Surface plugin-convention citations explicitly (e.g., "per
  feedback_no_backward_compat_shims, no compatibility shim -- migrate callers
  cleanly").
