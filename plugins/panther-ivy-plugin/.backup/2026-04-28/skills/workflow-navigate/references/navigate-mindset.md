# Navigate — Mindset & Anti-Rationalization

Cold-path guidance extracted from `navigate/SKILL.md` so the session-loaded
skill stays lean. Load this file when a workflow rejects routing advice and
you need to check the full mindset rules, or when you catch yourself
rationalizing past a routing decision.

## Mindset (always active)

**Compositional thinking**: Always ask — what does this isolate assume about its environment? What does it guarantee? Think in assume-guarantee contracts. Never break abstraction boundaries between isolates.

**RFC-first reasoning**: Start from the RFC requirement, not from code patterns. Ask "which RFC section does this implement?" before writing any monitor. Always add bracket tags (`# [rfcNNNN:X.Y]`).

**Verify-as-you-go**: Run `ivy_diagnostics(mode="structural")` and `ivy_verify` after every meaningful change — don't batch verification. Treat verification failures as immediate feedback, not deferred cleanup.

## Anti-Rationalization

| Thought | Reality |
|---------|---------|
| "I already know what to do" | Route to the correct workflow. Don't freelance. |
| "This is a quick fix" | Quick fixes in formal specs create unsound models. Route to verify. |
| "Let me just edit this one file" | Edits without verification break assume-guarantee contracts. Route to build or verify. |
| "The user just wants me to do it" | The user wants correct results. Workflows exist to ensure correctness. |
