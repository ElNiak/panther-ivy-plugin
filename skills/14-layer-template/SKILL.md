---
name: 14-Layer Template
description: This skill should be used when the user asks about "creating a new protocol model", "protocol specification architecture", "layer architecture", "14-layer template", "formal model structure", "protocol decomposition", "scaffolding a protocol", "Ivy model layers", or mentions structuring a new formal protocol specification in the PANTHER Ivy framework. Provides the structural template for decomposing any network protocol into modular Ivy specifications.
---

# 14-Layer Formal Model Template

## Overview

The 14-layer template provides a structural pattern for decomposing any network protocol into modular Ivy specifications. All three PANTHER methodologies (NCT, NACT, NSCT) share this template. The layers are organized into 4 groups: Core Protocol Stack, Entity Model, Infrastructure, and Optional Layers.

## Layer Reference

### Core Protocol Stack (Layers 1-9, Always Required)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 1 | Type Definitions | `{prot}_types.ivy` | Identifiers, bit vectors, enumerations — the foundation all other layers depend on |
| 2 | Application | `{prot}_application.ivy` | Data transfer semantics, application-level events |
| 3 | Security/Handshake | `{prot}_security.ivy` | Key establishment, handshake protocol |
| 4 | Frame/Message | `{prot}_frame.ivy` | Protocol Data Unit definitions — where protocol semantics live |
| 5 | Packet | `{prot}_packet.ivy` | Wire-level packet structure and encoding rules |
| 6 | Protection | `{prot}_protection.ivy` | Encryption/decryption procedures |
| 7 | Connection/State | `{prot}_connection.ivy` | Session lifecycle, state machine management |
| 8 | Transport Parameters | `{prot}_transport_parameters.ivy` | Negotiable parameters exchanged during handshake |
| 9 | Error Handling | `{prot}_error_code.ivy` | Error taxonomy and error code definitions |

### Entity Model (Layers 10-12, Always Required)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 10 | Entity Definitions | `ivy_{prot}_{role}.ivy` | Network participant instances (client, server, etc.) |
| 11 | Entity Behavior | `ivy_{prot}_{role}_behavior.ivy` | FSM and behavioral constraints (before/after monitors) |
| 12 | Shims | `{prot}_shim.ivy` | Bridge between formal model and real implementations |

### Infrastructure (Layers 13-14, Mostly Reusable)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 13 | Serialization/Deserialization | `{prot}_ser.ivy`, `{prot}_deser.ivy` | Wire format encoding/decoding |
| 14 | Utilities | `byte_stream.ivy`, `file.ivy`, `time.ivy`, `random_value.ivy`, `locale.ivy` | Common utilities |

### Optional Layers (Protocol-Dependent)

| Layer | When Needed |
|---|---|
| Security Sub-Protocol (`tls_stack/` or `dtls_stack/`) | Integrated TLS/DTLS security |
| FSM Modules (`{prot}_fsm/`) | Complex state machines |
| Recovery & Congestion (`{prot}_recovery/`, `{prot}_congestion/`) | Built-in reliability |
| Extensions (`{prot}_extensions/`) | Protocol extension mechanism |
| Attacks Stack (`{prot}_attacks_stack/`) | APT/NACT integration |
| Stream/Flow Management (`{prot}_stream.ivy`) | Multiplexed streams |

## Layer Dependencies

Build layers in dependency order:

```
Types (1) <- Foundation, no dependencies
  |-- Error Codes (9)
  |-- Transport Parameters (8)
  |-- Application (2)
  |-- Frame/Message (4) <- depends on Types, Error Codes
  |   |-- Packet (5) <- depends on Frame
  |   |   |-- Protection (6) <- depends on Packet
  |   |   +-- Serialization (13) <- depends on Packet, Frame
  |   +-- Connection (7) <- depends on Frame, Packet
  |-- Security (3) <- depends on Types, Connection
  +-- Entity Definitions (10) <- depends on Connection, Packet
      |-- Entity Behavior (11) <- depends on Entity Defs, all stack layers
      +-- Shims (12) <- depends on Entity Defs
```

## Genuinely Reusable Components

Only these components are identical across protocols:
- `byte_stream.ivy` — byte stream manipulation
- `file.ivy` — file I/O utilities
- `random_value.ivy` — random value generation
- The shim **pattern** (not implementation)
- The `_finalize()` **pattern** for end-state verification
- The `before`/`after` monitor **pattern** for specification

Everything else is protocol-specific, even within the template structure.

## Directory Structure per Protocol

```
protocol-testing/{prot}/
|-- {prot}_stack/              # Layers 1-9
|   |-- {prot}_types.ivy
|   |-- {prot}_application.ivy
|   |-- {prot}_security.ivy
|   |-- {prot}_frame.ivy
|   |-- {prot}_packet.ivy
|   |-- {prot}_protection.ivy
|   |-- {prot}_connection.ivy
|   |-- {prot}_transport_parameters.ivy
|   +-- {prot}_error_code.ivy
|-- {prot}_entities/           # Layers 10-12
|   |-- ivy_{prot}_client.ivy
|   |-- ivy_{prot}_server.ivy
|   |-- ivy_{prot}_client_behavior.ivy
|   +-- ivy_{prot}_server_behavior.ivy
|-- {prot}_shims/              # Layer 12
|   +-- {prot}_shim.ivy
|-- {prot}_utils/              # Layers 13-14
|   |-- {prot}_ser.ivy
|   |-- {prot}_deser.ivy
|   |-- byte_stream.ivy
|   |-- file.ivy
|   |-- time.ivy
|   +-- random_value.ivy
+-- {prot}_tests/
    |-- server_tests/
    |-- client_tests/
    +-- mim_tests/
```

## Scaffolding a New Protocol

### Minimal Viable Set
For a basic protocol model, start with these layers:
1. Types (1) — Always first
2. Frame/Message (4) — Protocol semantics
3. Packet (5) — Wire format
4. Connection (7) — State management
5. Entity Definitions (10) — Participant instances
6. Entity Behavior (11) — Behavioral constraints
7. Shims (12) — Implementation bridge

### Template Directory
Reference `protocol-testing/new_prot/` for the empty template structure:
```
new_prot/
|-- new_prot_stack/
|   +-- new_prot_application.ivy
|-- new_prot_entities/
|   |-- new_prot_endpoint.ivy
|   +-- ivy_new_prot_endpoint_behavior.ivy
|-- new_prot_shims/
|   +-- new_prot_shim.ivy
+-- new_prot_utils/
    |-- new_prot_type.ivy
    |-- new_prot_ser.ivy
    |-- new_prot_deser.ivy
    |-- new_prot_byte_stream.ivy
    |-- new_prot_file.ivy
    +-- new_prot_time.ivy
```

Use `/nct-new-protocol` command to interactively scaffold from this template.

## Decision Matrix for Template Selection

| Protocol Property | Template Impact |
|---|---|
| Connection-oriented (TCP-based)? | Simplified packet structure, TCP stream layer |
| Built-in reliability? | Add recovery/congestion modules |
| Multiplexed streams? | Add stream management + per-stream FSM |
| Integrated security? | Add TLS/DTLS sub-protocol stack |
| Peer-to-peer? | Symmetric entities (Speaker/Peer instead of Client/Server) |
| Pub/Sub pattern? | Add broker entity + topic/subscription management |
| Extension mechanism? | Add extensions module |
| Stateless? | Simplify connection/state management significantly |
| Tunneling? | Add encapsulation + Security Association management |
| Real-time? | Add timing constraints + FEC recovery |

## Tools for Template Work

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
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` — Formal verification
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` — Test compilation
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` — Model introspection
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` — Fast structural lint
