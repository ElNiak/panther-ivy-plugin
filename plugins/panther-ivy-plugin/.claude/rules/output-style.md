---
paths: ["**/skills/*/SKILL.md"]
---

# Output Style

Each workflow skill's output formatting is managed by the plugin style system.
Follow the style directives injected via `additionalContext`; they carry the
active workflow overlay and phase modifier. Tool results that arrive
pre-formatted in `hookSpecificOutput` are already in their final form — read
them as-is and pass them through to the user unchanged.
