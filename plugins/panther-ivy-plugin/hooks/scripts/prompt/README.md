# prompt/

Hooks that shape the system prompt at session entry and per-turn boundaries.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `using-plugin.py` | SessionStart | (none) | Inject the panther-ivy-plugin overview into the session system prompt. |
| `style.py` | UserPromptSubmit | (none) | Compose / apply the active output style on every user turn. |

See `.claude/rules/output-style.md` for the systemMessage prefix table.
