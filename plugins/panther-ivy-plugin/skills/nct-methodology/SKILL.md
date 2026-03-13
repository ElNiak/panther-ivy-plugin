---
name: NCT Methodology
description: This skill should be used when the user asks about "compositional testing", "protocol specification", "formal verification", "NCT", "specification-based testing", "role-based testing", "test against IUT", "Ivy protocol testing", or mentions writing formal protocol specifications that generate test traffic. Provides step-by-step NCT workflow guidance for the PANTHER Ivy framework.
---

# NCT — Network-Centric Compositional Testing

## Overview

NCT is a specification-based testing methodology where a formal Ivy protocol specification plays one role (client, server, or man-in-the-middle) against an Implementation Under Test (IUT). The specification generates test traffic via Z3/SMT symbolic execution and monitors received packets against formal assertions.

## Core Concepts

### Role Inversion
The Ivy tester's role is the **opposite** of what it tests:
- Testing a server IUT → Ivy acts as a formal client (`{prot}_server_test_*.ivy` files)
- Testing a client IUT → Ivy acts as a formal server (`{prot}_client_test_*.ivy` files)
- MIM testing → Ivy acts as man-in-the-middle (`{prot}_mim_test_*.ivy` files)

### Specification Structure
Protocol specs use **monitors** (before/after clauses) attached to protocol events:

- **before clauses** — Preconditions/guards. Define what must hold before an event occurs. If the precondition fails, the event is blocked.
- **after clauses** — State updates/checks. Record history by updating shared variables. Check specification compliance of received data.
- **_finalize()** — End-state verification. Called when the test completes. Performs heuristic checks (e.g., data was received, no errors occurred).

### Test Traffic Generation
Specifications use `export` to declare actions that the test mirror generates randomly:
```ivy
export frame.ack.handle
export frame.stream.handle
export packet_event
export client_send_event
```
Z3/SMT solving ensures generated traffic complies with specification constraints.

## NCT Workflow

### Step 1: Select Target Protocol and RFC
Identify the protocol to test and the RFC(s) defining it. Extract testable requirements (MUST, SHOULD, MAY statements).

### Step 2: Decompose into 14 Formal Layers
Map RFC sections to the 14-layer template. Use the `14-layer-template` skill for detailed guidance. Minimum viable set:
1. Types → Frames → Packets → Connection (core data flow)
2. Entity definitions → Entity behavior → Shims (participants)
3. Test specifications (verification)

### Step 3: Write Type Definitions
Start with `{prot}_types.ivy` — the foundation layer defining identifiers, bit vectors, enumerations used throughout the model.

### Step 4: Build Core Protocol Stack
Progress through layers in dependency order:
- Frame/Message layer (`{prot}_frame.ivy`) — PDU definitions
- Packet layer (`{prot}_packet.ivy`) — wire-level structure
- Protection layer (`{prot}_protection.ivy`) — encryption/decryption
- Connection layer (`{prot}_connection.ivy`) — session lifecycle

### Step 5: Define Entity Roles
Create entity definitions for each protocol participant:
- `ivy_{prot}_client.ivy` — client instance
- `ivy_{prot}_server.ivy` — server instance
- Optionally: MIM, attacker roles

### Step 6: Write Behavioral Constraints
Encode RFC requirements as before/after monitors in `ivy_{prot}_{role}_behavior.ivy`. This is the largest and most complex protocol-specific code.

### Step 7: Create Test Specifications
Write role-specific test files:
```ivy
#lang ivy1.7
include order
include {prot}_infer
include file
include ivy_{prot}_shim_client
include ivy_{prot}_client_behavior

after init {
    # Initialize sockets, TLS, transport parameters
}

# Export actions for test mirror generation
export frame.ack.handle
export frame.stream.handle
export packet_event

# End-state verification
export action _finalize = {
    require is_no_error;
    require conn_total_data(the_cid) > 0;
}
```

### Step 8: Verify with ivy-tools
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` to verify formal properties:
- Isolate assumptions
- Invariants
- Safety properties

### Step 9: Compile Test
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` with `target=test` to produce executable test binary.

### Step 10: Execute Against IUT
Run compiled test against the implementation via PANTHER experiment framework.

## Tools for NCT

### Navigation and editing

Use Claude's built-in tools:
- `Read` — Read file contents
- `Grep` — Search across files
- `Glob` — Find files by pattern
- `Edit` — Modify code in place
- `Write` — Create new files

Native Ivy LSP provides go-to-definition, find-references, hover, and instant diagnostics for `.ivy` files.

### Verification and analysis

Use ivy-tools MCP tools:

| Step | Tool | Usage |
|---|---|---|
| Formal verification | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` | Check isolate/invariant/safety properties |
| Compile tests | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` | Build test executables (target=test) |
| Inspect model | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` | View types, relations, actions, invariants |
| Fast structural lint | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` | Quick structural checks |

**IMPORTANT**: Always use ivy-tools MCP tools for Ivy verification operations. Never run ivy_check, ivyc, ivy_show, or ivy_to_cpp directly via Bash.

## Directory Structure

```
protocol-testing/{prot}/
├── {prot}_stack/          # Core protocol model (layers 1-9)
├── {prot}_entities/       # Entity definitions and behavior
├── {prot}_shims/          # Implementation bridge
├── {prot}_utils/          # Serialization, utilities
└── {prot}_tests/
    ├── server_tests/      # Tests targeting server IUTs
    ├── client_tests/      # Tests targeting client IUTs
    └── mim_tests/         # Man-in-the-middle tests
```

## QUIC Reference Example

The QUIC model (`protocol-testing/quic/`) is the most complete NCT implementation with 50+ test variants covering:
- Stream handling, connection close, retry, migration
- Transport parameter validation, error conditions
- 0-RTT, congestion control, loss recovery
- Version negotiation, timeout handling

Examine `quic_server_test.ivy` as the canonical test structure example.
