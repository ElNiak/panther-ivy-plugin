---
name: set-workspace
description: Set the active Ivy protocol workspace to restrict edits and include resolution to a specific protocol. Use when starting work on a protocol, or to check which workspace is active.
---

# Set Active Workspace

Set or query the active protocol workspace for Ivy formal model development.

## Usage

**With argument** — activate a workspace:
```
/set-workspace quic
/set-workspace apt
/set-workspace quic client+server
```

**Without argument** — show current workspace and available groups:
```
/set-workspace
```

## Behavior

1. If called with a valid protocol name: call `ivy_workspace(action="set", target="<protocol>")`
2. If called with protocol + roles (e.g., `quic client+server`): call `ivy_workspace(action="set", target="<protocol>", roles="<roles>")`
3. If called with a `.ivy` test file: call `ivy_workspace(action="set", target="<file>")`
4. If called with no argument or unknown target: call `ivy_workspace(action="list")` to show current workspace and available groups
5. Always show the current workspace status as the first line of output

After setting a workspace:
- Edits to `.ivy` files outside the active protocol will be **blocked** by the edit isolation hook
- Include resolution will only search within active layers + stdlib
- All MCP tools scope their results to the active workspace

## Example Output

```
Current workspace: quic (set by: explicit)
Active layers: quic, quic_tests
Files in scope: 170
Available workspaces: quic, apt, apt_quic, minip, bgp, coap, scaffolds
```

## Related
- `/clear-workspace` — remove workspace restrictions
- `ivy_workspace` MCP tool — programmatic workspace management
