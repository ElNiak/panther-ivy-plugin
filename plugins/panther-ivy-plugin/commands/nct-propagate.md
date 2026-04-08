---
name: nct-propagate
description: "DEPRECATED: Use the build workflow instead. This command will be removed."
arguments:
  - name: change
    description: "Natural language description of the change (e.g., 'add seq_num : byte to ping_packet')"
    required: true
  - name: protocol
    description: Target protocol for propagation (e.g., minip, quic)
    required: true
---

<!-- MODE: DEEP — multi-tool analysis, file edits, compilation, verification -->

# /nct-propagate

Propagate an Ivy type change across serializer/deserializer state machines, with impact analysis, user approval gates, and compilation validation.

## Prerequisites

- The `ivy-tools` MCP server must be running (provides `ivy_find_variants`, `ivy_serdes_correlation`, `ivy_change_impact`, `ivy_compile`)
- The `serena` MCP server must be running for file editing (provides `read_file`, `replace_content`)

**Serena pre-flight**: Call `mcp__plugin_panther-ivy-plugin_serena__get_current_config()`. If this fails, output: "Serena MCP server is not running. Start it with the start-serena.sh script or run `/nct-serena-health` to diagnose."

## Workflow

### Step 0 — Workspace

Set the ivy-lsp workspace to the target protocol:

```
Call: mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workspace(action="set", target="{protocol}")
```

If the index is stale or missing, rebuild it:

```
Call: mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_index(protocol="{protocol}")
```

Wait for indexing to complete before proceeding.

### Step 1 — Parse Change Description

Parse the user's change description (passed as the `change` argument) into a structured spec:

- `type_name`: The Ivy type being changed (e.g., `ping_packet`, `frame`)
- `change_type`: Either `add_field` or `add_variant`
- `field_spec` or `variant_spec`: The field/variant definition (e.g., `seq_num : byte`)
- `position`: Where to insert (e.g., "after payload")

If the description is ambiguous, ask the user to clarify before proceeding.

### Step 2 — Analysis

Call the three analysis tools:

1. **Type structure:** `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_find_variants(type_name="<type>")` — validates the type exists and shows current structure
2. **Ser/deser mapping:** `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_serdes_correlation(type_name="<type>")` — finds which ser/deser files handle this type
3. **Impact categorization:** `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_change_impact(type_name="<type>", change_type="<add_field|add_variant>")` — returns `auto_propagate`, `manual_review`, and `unaffected` file lists

The `ivy_change_impact` output is the **authoritative** classification. Do not override it.

### Step 3 — Present Plan

Present the propagation plan to the user:

```
Propagation plan for: <change description>

Auto-propagate (<N> files):
  1. <file> — <edit description>
  2. <file> — <edit description>
  3. <file> — <edit description>

Manual review needed (<M> files):
  - <file> — <reason>
  - <file> — <reason>
  ...

WARNING: <any hardcoded constants found in deser files>

Proceed? (y/n)
```

If the user declines, abort the propagation.

### Step 4 — Execute Edits

**IMPORTANT:** Use the `propagation-patterns` skill for pattern knowledge. It contains the exact C++ patterns, encoding table, and asymmetry warnings.

For each file in `auto_propagate`, in order:

1. **Read** the file via `mcp__plugin_panther-ivy-plugin_serena__read_file`
2. **Store** the full original content in the transaction log (hold in conversation context)
3. **Generate** the specific edit guided by the propagation-patterns skill
4. **Present** the proposed diff to the user for approval
5. **On approval**, apply via `mcp__plugin_panther-ivy-plugin_serena__replace_content`

If the user **rejects** a diff mid-propagation:
- Ask: "Revert already-edited files and abort, or skip this file and continue?"
- **Revert and abort:** Restore all previously edited files from the transaction log
- **Skip and continue:** Leave previous edits, skip this file, proceed to remaining files

### Step 5 — Validation

After all edits are applied:

1. Compile the server-side test: `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile(relative_path="{protocol}_tests/server_tests/")`
2. If that passes, compile the client-side test: `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile(relative_path="{protocol}_tests/client_tests/")`
3. **Both pass:** Report success. Print the manual-review file list with reasons. Print any hardcoded constant warnings.
4. **Either fails:** Report the compilation error. Ask the user: "Revert all changes, or keep for debugging?"

### Step 6 — Revert (on failure or user request)

For each entry in the transaction log, in **reverse** order:

1. Write back the full original content via `mcp__plugin_panther-ivy-plugin_serena__replace_content`
2. Confirm the file was restored

After revert, report which files were restored.

## Notes

- All file operations go through panther-serena MCP tools, not native Read/Edit/Write tools. This ensures the same workflow works in future headless mode.
- The transaction log is held in conversation context (not persisted). It is discarded when the command completes.
- Hardcoded constants in deserializers (e.g., `payload_length`, iteration caps) are semantic values that `ivyc` cannot validate. Always warn the user about these.
