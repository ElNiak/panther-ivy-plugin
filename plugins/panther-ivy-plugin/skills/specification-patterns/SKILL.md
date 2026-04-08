---
name: specification-patterns
description: "Internal knowledge skill — layer selection, pattern scaffolding templates. Do not invoke directly; loaded by build (Phase 2 blueprint)."
allowed-tools: "Read Grep Glob ToolSearch"
---

# Specification Patterns: 14-Layer Template and Formal Model Patterns

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill combines the 14-layer structural template with the formal model pattern library. Use it when creating new protocol specifications or adding patterns to existing ones.

---

## 14-Layer Formal Model Template

### Overview

The 14-layer template provides a structural pattern for decomposing any network protocol into modular Ivy specifications. All three PANTHER methodologies (NCT, NACT, NSCT) share this template. The layers are organized into 4 groups.

### Layer Reference

#### Core Protocol Stack (Layers 1-9, Always Required)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 1 | Type Definitions | `{prot}_types.ivy` | Identifiers, bit vectors, enumerations -- the foundation |
| 2 | Application | `{prot}_application.ivy` | Data transfer semantics, application-level events |
| 3 | Security/Handshake | `{prot}_security.ivy` | Key establishment, handshake protocol |
| 4 | Frame/Message | `{prot}_frame.ivy` | Protocol Data Unit definitions -- protocol semantics |
| 5 | Packet | `{prot}_packet.ivy` | Wire-level packet structure and encoding rules |
| 6 | Protection | `{prot}_protection.ivy` | Encryption/decryption procedures |
| 7 | Connection/State | `{prot}_connection.ivy` | Session lifecycle, state machine management |
| 8 | Transport Parameters | `{prot}_transport_parameters.ivy` | Negotiable parameters exchanged during handshake |
| 9 | Error Handling | `{prot}_error_code.ivy` | Error taxonomy and error code definitions |

#### Entity Model (Layers 10-12, Always Required)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 10 | Entity Definitions | `ivy_{prot}_{role}.ivy` | Network participant instances |
| 11 | Entity Behavior | `ivy_{prot}_{role}_behavior.ivy` | FSM and behavioral constraints (before/after monitors) |
| 12 | Shims | `{prot}_shim.ivy` | Bridge between formal model and real implementations |

#### Infrastructure (Layers 13-14, Mostly Reusable)

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 13 | Serialization/Deserialization | `{prot}_ser.ivy`, `{prot}_deser.ivy` | Wire format encoding/decoding |
| 14 | Utilities | `byte_stream.ivy`, `file.ivy`, `time.ivy`, `random_value.ivy` | Common utilities |

#### Optional Layers (Protocol-Dependent)

| Layer | When Needed |
|---|---|
| Security Sub-Protocol (`tls_stack/` or `dtls_stack/`) | Integrated TLS/DTLS security |
| FSM Modules (`{prot}_fsm/`) | Complex state machines |
| Recovery & Congestion (`{prot}_recovery/`, `{prot}_congestion/`) | Built-in reliability |
| Extensions (`{prot}_extensions/`) | Protocol extension mechanism |
| Attacks Stack (`{prot}_attacks_stack/`) | APT/NACT integration |
| Stream/Flow Management (`{prot}_stream.ivy`) | Multiplexed streams |

### Layer Dependencies

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

### Genuinely Reusable Components

Only these components are identical across protocols:
- `byte_stream.ivy` -- byte stream manipulation
- `file.ivy` -- file I/O utilities
- `random_value.ivy` -- random value generation
- The shim **pattern** (not implementation)
- The `_finalize()` **pattern** for end-state verification
- The `before`/`after` monitor **pattern** for specification

Everything else is protocol-specific, even within the template structure.

### Scaffolding a New Protocol

#### Minimal Viable Set
For a basic protocol model, start with these 7 layers:
1. Types (1) -- Always first
2. Frame/Message (4) -- Protocol semantics
3. Packet (5) -- Wire format
4. Connection (7) -- State management
5. Entity Definitions (10) -- Participant instances
6. Entity Behavior (11) -- Behavioral constraints
7. Shims (12) -- Implementation bridge

#### Template Directory
Reference `protocol-testing/new_prot/` for the empty template structure. Use `/nct-scaffold type=protocol` to interactively scaffold.

### Decision Matrix for Template Selection

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

### Directory Structure per Protocol

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

---

## Formal Model Pattern Library

7 recurring patterns across PANTHER Ivy protocol models (QUIC, BGP, CoAP, MiniP). See `references/pattern-library-detail.md` for full code examples and decision points.

### Pattern Overview

| # | Pattern | Layer | Purpose |
|---|---------|-------|---------|
| 1 | **Variants** | 4 | PDU type hierarchy (message/frame/packet) |
| 2 | **Modules** | 6 | Parameterized reusable components |
| 3 | **Entities** | 10 | Protocol participants (client/server/speaker) |
| 4 | **Monitors** | 11 | Behavioral constraints (before/after) |
| 5 | **Shims** | 12 | Network I/O bridge (socket layer) |
| 6 | **Serdes** | 13 | Wire-format serialization/deserialization |
| 7 | **Include Chain** | all | Layer composition via include ordering |

### Pattern Dependencies and Scaffolding Order

```
variants (no deps)
  +-- serdes (needs variant tags for state machine)
  +-- monitors (constrain variant event actions)
entity (no deps)
module (no deps)
  +-- shim (bridges entities + serdes to network)
```

**Scaffolding order**: variants -> entity -> module -> serdes -> monitors -> shim

### Composition Rules

1. **Every protocol needs**: variants + entity + shim + serdes (minimum viable model)
2. **Monitors are optional** but recommended for testing
3. **Modules are optional** -- only needed for reusable parameterized components
4. **Include chains** must be consistent -- no circular dependencies

### Using the Pattern Library

Add patterns: `/nct-add-pattern {protocol} all`

Analyze patterns with `ivy_patterns` MCP tool (`mode="analyze"`, `"validate"`, `"compare"`). Template files in `protocol-testing/patterns/` with registry `pattern_catalog.yaml`.

## Reference Files

- **references/pattern-library-detail.md** -- Full formal model pattern library with code examples

## Integration

- **LOADED BY:** ivy-workflow-orchestrator Phase 2 (Plan)

**Related skills:**
- **methodology-reference** -- Layer decomposition in NCT/NACT/NSCT workflows
- **ivy-writing-guide** -- Ivy language reference for writing layers
- **ivy-toolkit** -- MCP tool parameters for pattern analysis

**Related agents:**
- **methodology-guide** -- Interactive workflow using these patterns
- **spec-analyst** -- Specification navigation across layers

**Related commands:**
- `/nct-scaffold type=protocol` -- Scaffolds from the 14-layer template
- `/nct-add-pattern` -- Add a pattern to an existing specification
