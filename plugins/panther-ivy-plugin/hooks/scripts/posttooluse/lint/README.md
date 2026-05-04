# posttooluse/lint/

PostToolUse linters for `.ivy` and `.py` files written / edited inside the workspace.

| File | Event | Matcher | Purpose |
|---|---|---|---|
| `ivy.py` | PostToolUse | `Write\|Edit` | Structural lint of `.ivy` files (missing language headers, malformed isolates). |
| `python-format.py` | PostToolUse | `Write\|Edit` | Auto-fix `.py` files via ruff. |
