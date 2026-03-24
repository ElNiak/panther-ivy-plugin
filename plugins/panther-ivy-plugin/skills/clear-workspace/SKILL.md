---
name: clear-workspace
description: Remove active workspace restrictions, allowing edits to all protocol files. Use when you need to work across multiple protocols.
---

# Clear Active Workspace

Remove the active workspace restriction, allowing edits to all protocols.

## Usage

```
/clear-workspace
```

## Behavior

1. Call `ivy_workspace(action="clear")`
2. Report confirmation: "Workspace cleared. All protocols are now in scope."

After clearing:
- Edits to any `.ivy` file are allowed
- Include resolution searches all layers
- MCP tools return results across all protocols

## Related
- `/set-workspace` — activate a workspace restriction
