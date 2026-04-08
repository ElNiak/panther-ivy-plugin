---
name: workspace-management
description: "DEPRECATED — workspace management stays as hooks only. Will be removed in a future version."
---

# Workspace Management

Workspace scoping prevents cross-protocol collisions by restricting `.ivy` file edits to the active protocol directory.

## Setting a Workspace

Call the MCP tool to activate workspace scoping:

```
ivy_workspace(action="set", target="<protocol>")
```

Optional role filter:
```
ivy_workspace(action="set", target="<protocol>", roles="client+server")
```

**Available workspaces:** `quic`, `apt`, `apt_quic`, `minip`, `bgp`, `coap`, `scaffolds`

## Clearing a Workspace

Remove all restrictions:

```
ivy_workspace(action="clear")
```

## Checking Current Workspace

```
ivy_workspace(action="get")
```

## Auto-Detection

When no workspace is explicitly set:
- The SessionStart hook detects the workspace from the project directory
- Per-protocol `.ivyworkspace` markers auto-scope when opening protocol files
- The progressive narrowing system suggests scoping after cross-protocol edits

## Scoping Rules

- **Writes** to `.ivy` files outside the active protocol are blocked
- **Reads** across protocols are always allowed
- Stdlib files (`ivy/include/1.7/`) are always accessible
- All MCP tool `relative_path` and `test_file` parameters are workspace-relative
