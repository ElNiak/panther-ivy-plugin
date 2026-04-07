---
name: ivy-lsp-walkthrough
description: Use when you need a concrete end-to-end example of LSP + MCP coordination on a real protocol specification
loads: [lsp-patterns, ivy-writing-guide]
---

# End-to-End Walkthrough: Adding an RFC Requirement

This walkthrough demonstrates the full plugin toolchain — LSP for navigation, MCP for analysis/verification — on the real QUIC specification. It shows how to add explicit enforcement of an RFC requirement.

## Scenario

**Requirement**: rfc9000:7.3 "Authenticating Connection IDs"

> The values provided by a peer for these transport parameters MUST match the values that an endpoint used in the Destination and Source Connection ID fields of Initial packets that it sent.

**Goal**: Add a formal monitor that enforces this MUST requirement in the QUIC specification, with proper RFC traceability.

## Prerequisites

- Ivy LSP server running (configured via `.lsp.json`)
- MCP ivy-tools server running (configured via `.mcp.json`)
- Working directory includes `protocol-testing/quic/`
- **Workspace**: Set active workspace with `/set-workspace quic` before editing to ensure include resolution is scoped to the QUIC protocol and writes are isolated to the active protocol directory.

## Step 1: Find the Relevant Action Using LSP

### 1a. Get the file outline

Start by understanding what `quic_application.ivy` contains:

```
LSP(operation="documentSymbol", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=1, character=1)
```

**Returns**: Hierarchy of symbols including `app_server_open_event`, `app_send_event`, `map_cids`, `used_cid`, `stream_app_data`, etc.

This immediately tells you which actions and state exist in this layer.

### 1b. Search for CID-related symbols across workspace

```
LSP(operation="workspaceSymbol", filePath="protocol-testing/quic/quic_stack/quic_transport_parameters.ivy", line=32, character=8)
```

Point at `original_destination_connection_id` (line 32) to find CID-related transport parameter symbols across all files.

**Finds**: `original_destination_connection_id` in `quic_transport_parameters.ivy`, `initial_source_connection_id` at line 145, and their usages in config files.

## Step 2: Explore Definitions Using LSP

### 2a. Jump to `map_cids` definition

```
LSP(operation="goToDefinition", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=104, character=10)
```

Position at the `map_cids` call inside `around app_server_open_event`. Navigates to line 109:

```ivy
action map_cids(dcid:cid,scid:cid) = {
    used_cid(dcid) := true;
    connected(dcid) := true;
    connected_to(dcid) := scid
}
```

### 2b. Get type signature via hover

```
LSP(operation="hover", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=109, character=8)
```

**Returns**: `action map_cids(dcid:cid, scid:cid)` — confirms parameter names and types without reading the whole file.

### 2c. Understand the connection event

```
LSP(operation="hover", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=32, character=8)
```

**Returns**: `action app_server_open_event(src:ip.endpoint, dst:ip.endpoint, scid:cid, dcid:cid)` — the action that establishes a connection and calls `map_cids`.

## Step 3: Find Existing Monitors Using LSP

### 3a. Find all references to `map_cids`

```
LSP(operation="findReferences", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=109, character=8)
```

**Returns**: All call sites and monitors — `quic_application.ivy` lines 104-105 (inside `around app_server_open_event`).

### 3b. Find all references to `connected_to`

```
LSP(operation="findReferences", filePath="protocol-testing/quic/quic_stack/quic_application.ivy", line=112, character=5)
```

**Returns**: All files using `connected_to` — behavior files (`ivy_quic_client_server_behavior.ivy` lines 232, 417; `ivy_quic_server_behavior.ivy` lines 277, 463) where existing monitors use `connected_to(the_cid)` to verify CID associations.

### 3c. Find transport parameter usages

```
LSP(operation="findReferences", filePath="protocol-testing/quic/quic_stack/quic_transport_parameters.ivy", line=145, character=8)
```

**Returns**: All files referencing `initial_source_connection_id` — config files where transport parameters are set, and test files where they are checked.

**Key insight from Steps 1-3**: LSP resolved cross-file references that Grep would miss or return noisy results for. `findReferences` on `connected_to` found exact usage sites in behavior files, not string matches in comments.

## Step 4: Check Coverage Gaps Using MCP

### 4a. Check requirement coverage

```
MCP: ivy_coverage(mode="stats", relative_path="protocol-testing/quic/quic_stack/")
```

**Returns**: Coverage statistics by RFC section and normative level (MUST/SHOULD/MAY). Look for `rfc9000:7.3` — if coverage is low, this confirms the need for a new monitor.

### 4b. Identify specific gaps

```
MCP: ivy_coverage(mode="gaps", test_file="protocol-testing/quic/")
```

**Returns**: Unguarded state variables, uncovered RFC requirements, and phantom references. Look for `rfc9000:7.3` in the uncovered list.

## Step 5: Write the New Monitor

Based on the exploration, we know:
- `map_cids` establishes the CID association at connection setup
- Transport parameters carry `initial_source_connection_id.scid` and `original_destination_connection_id.dcid`
- The requirement says these MUST match the actual CIDs used in Initial packets

Add an after-monitor to the behavior file that validates CID consistency:

```ivy
# Verify transport parameter CIDs match Initial packet CIDs
# Per rfc9000:7.3, the values in transport parameters MUST match
# the CIDs used in the Initial packets.
after tls.handshake_data_event(src:ip.endpoint, dst:ip.endpoint, data:stream_data) {
    if initial_source_connection_id.is_set(trans_params(the_cid)) {
        require initial_source_connection_id.value(trans_params(the_cid)).scid = the_cid;  # [rfc9000:7.3]
    }
}
```

Use the `Edit` tool to insert this monitor in the appropriate behavior file.

## Step 6: Lint (Automatic + Manual)

The PostToolUse hook runs `ivy_diagnostics(mode="structural")` automatically after the Edit. Check its output for structural issues.

Also run manually for certainty:

```
MCP: ivy_diagnostics(mode="structural", relative_path="protocol-testing/quic/quic_entities_behavior/ivy_quic_server_behavior.ivy")
```

**Expected**: 0 errors, 0 warnings if the monitor syntax is correct.

## Step 7: Verify Using MCP

Run formal verification:

```
MCP: ivy_verify(relative_path="protocol-testing/quic/quic_entities_behavior/ivy_quic_server_behavior.ivy")
```

**If PASS**: The new monitor is consistent with the existing model.

**If FAIL**: Use the Workflow C diagnosis workflow from the `ivy-toolkit` skill — read the error, use LSP `goToDefinition` to locate the failing symbol, `hover` for type info, `findReferences` to trace constraints.

## Step 8: Check Traceability Using MCP

Confirm the new bracket tag is registered:

```
MCP: ivy_coverage(mode="matrix", relative_path="protocol-testing/quic/")
```

**Expected**: `rfc9000:7.3` now appears as covered, mapped to the new assertion in the behavior file.

## Key Takeaways

| Phase | Steps | Tools Used | Purpose |
|-------|-------|-----------|---------|
| **Navigation** | 1-3 | LSP (documentSymbol, workspaceSymbol, goToDefinition, findReferences, hover) | Understand code semantically |
| **Analysis** | 4 | MCP (ivy_coverage mode="stats", ivy_coverage mode="gaps") | Identify what's missing |
| **Editing** | 5 | Edit | Write the new monitor |
| **Validation** | 6-8 | MCP (ivy_diagnostics, ivy_verify, ivy_coverage mode="matrix") | Confirm correctness and traceability |

**LSP was used for Steps 1-3** (5 distinct operations) to navigate the codebase semantically.
**MCP was used for Steps 4, 6-8** (4 distinct tools) for analysis and verification.
**Grep was NOT needed** because LSP provided semantic navigation across includes.

## Tool Selection Summary

```
Need to FIND something?     --> LSP (goToDefinition, findReferences, workspaceSymbol)
Need to UNDERSTAND type?     --> LSP (hover)
Need to SEE structure?       --> LSP (documentSymbol)
Need to CHECK correctness?   --> MCP (ivy_diagnostics, ivy_verify)
Need to CHECK coverage?      --> MCP (ivy_coverage mode="stats", ivy_coverage mode="gaps")
Need to CHECK traceability?  --> MCP (ivy_coverage mode="matrix")
Need to SEARCH text/regex?   --> Grep
Need to READ file content?   --> Read
```

## Integration

- **CONTEXT:** Demonstrates LSP + MCP coordination used across all orchestrator phases

**Prerequisite:** `lsp-patterns` -- LSP invocation patterns; `ivy-toolkit` -- MCP tool architecture and selection.

**Related skills:**
- **lsp-patterns** -- LSP invocation patterns used in this walkthrough
- **ivy-toolkit** -- MCP tool parameters and coordination workflows
- **ivy-writing-guide** -- Ivy syntax for editing
- **workflow-reference** -- Verification and quality gate workflows

**Related agents:**
- **spec-analyst** -- Specification navigation and verification
- **methodology-guide** -- Methodology workflow execution
