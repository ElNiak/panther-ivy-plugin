---
name: specification-patterns
description: "Use when structuring a new formal protocol specification into modular Ivy layers, choosing which layers to scaffold first, or selecting formal model patterns (variants, serdes, shims, monitors, entities, modules)."
---

# Specification Patterns: 14-Layer Template and Formal Model Patterns

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

This section documents the 7 recurring patterns found across PANTHER Ivy protocol models (QUIC, BGP, CoAP, MiniP).

### Pattern Overview

| # | Pattern | Layer | Purpose | Example Protocol |
|---|---------|-------|---------|-----------------|
| 1 | **Variants** | 4 | PDU type hierarchy (message/frame/packet) | BGP messages, QUIC frames |
| 2 | **Modules** | 6 | Parameterized reusable components | QUIC protection, crypto |
| 3 | **Entities** | 10 | Protocol participants (client/server/speaker) | MiniP endpoints, BGP speakers |
| 4 | **Monitors** | 11 | Behavioral constraints (before/after) | BGP speaker behavior |
| 5 | **Shims** | 12 | Network I/O bridge (socket layer) | MiniP UDP shim, BGP TCP shim |
| 6 | **Serdes** | 13 | Wire-format serialization/deserialization | MiniP ping_ser, BGP bgp_ser |
| 7 | **Include Chain** | all | Layer composition via include ordering | All protocols |

### Pattern Dependencies

```
variants (no deps)
  +-- serdes (needs variant tags for state machine)
  +-- monitors (constrain variant event actions)
entity (no deps)
module (no deps)
  +-- shim (bridges entities + serdes to network)
```

**Scaffolding order**: variants -> entity -> module -> serdes -> monitors -> shim

### 1. Variants Pattern

**Purpose**: Define PDU (Protocol Data Unit) type hierarchies -- the messages, frames, or packets your protocol exchanges.

**When to use**: Every protocol needs this. It is the foundational data model.

**Decision points**:
- **Struct fields**: What fields does each message type have?
- **Dispatch method**: How are sub-types identified? (type field, first byte, TLV)
- **Nesting**: Does a message contain sub-messages?

**Key structure**:
```ivy
object {prot}_message = {
    type this = struct {
        msg_type : {prot}_message_type,
        payload  : stream_data
    }
}

action {prot}_message_event(src:{prot}_id, dst:{prot}_id, msg:{prot}_message) = {}

around {prot}_message_event(src, dst, msg) {
    require connection_active(src);
    ...
    if ~_generating {
        if msg.msg_type = {prot}_message_type.type_a {
            var sub := {prot}_type_a_serdes.from_bytes(msg.payload);
            call {prot}_type_a_event(src, dst, sub);
        }
    }
}
```

### 2. Modules Pattern

**Purpose**: Parameterized, reusable protocol components that can be instantiated with different types.

**When to use**: When you have a component that works with different type parameters.

**Cross-protocol example**: QUIC `quic_protection(tls_id, tls)` -- packet encryption/decryption parameterized by TLS type.

### 3. Entities Pattern

**Purpose**: Define protocol participants -- the endpoints that send and receive messages.

**Decision: Asymmetric vs Symmetric**:
- **Asymmetric** (client/server): Different roles have different behavior. Use `entity_role_pair_template.ivy`.
- **Symmetric** (speaker/peer): Both sides use the same behavior. Use `entity_symmetric_template.ivy`.

**Key structure**:
```ivy
object {prot}_endpoint = {
    type this
    module {role}_ep(address:ip.addr, port:ip.port) = {
        variant this of {prot}_endpoint = struct { }
        individual ep : ip.endpoint
        after init {
            ep.protocol := ip.{transport};
            ep.addr := address;
            ep.port := port;
        }
    }
}
```

### 4. Monitors Pattern

**Purpose**: Constrain action behavior with before/after/around blocks. This is where protocol requirements are formally specified.

**Decision points**:
- **`if _generating` guard**: Use in `before` blocks to constrain test traffic generation
- **Which actions to monitor**: Start with the top-level message event
- **Field constraints**: What values must fields have?

**Key structure**:
```ivy
before {prot}_message_event(src, dst, msg) {
    if _generating {
        require src = {prot}_ivy_instance.id;
        require dst = {prot}_impl_instance.id;
        require msg.msg_type = expected_type;
    }
}
```

### 5. Shims Pattern

**Purpose**: Bridge between the formal specification and real network I/O.

**Decision: UDP vs TCP**:
- **UDP**: Stateless, simpler. (MiniP, CoAP, QUIC)
- **TCP**: Stateful (connection tracking with `isup`/`pend` relations). (BGP, HTTP)

**Key structure (UDP)**:
```ivy
implement {prot}_net.recv(host:endpoint_id, s:{prot}_net.socket, src:ip.endpoint, pkts:arr) {
    if host = endpoint_id.server {
        call server.behavior(host, s, src, pkts);
    } else if host = endpoint_id.client {
        call client.behavior(host, s, src, pkts);
    }
}
instance {prot}_serdes : serdes({prot}_packet, stream_data, {prot}_ser, {prot}_deser)
```

### 6. Serdes Pattern

**Purpose**: Serialize Ivy objects to wire bytes and deserialize wire bytes back to Ivy objects.

**Decision: Binary vs JSON**:
- **Binary**: Fixed-width fields, tag-based encoding. (MiniP, BGP, QUIC)
- **JSON**: Text-based key-value encoding. (REST APIs)

**Critical invariant**: Enum states in ser and deser must correspond to variant tags 1:1.

### 7. Include Chain Pattern

**Purpose**: Compose layers by including files in dependency order.

**Recommended include ordering**:
1. Type definitions
2. Application layer
3. Packet/frame definitions
4. Utility includes
5. Ser/deser files
6. Entity definitions
7. Behavior specifications
8. Network/shim layer
9. Message dispatch
10. Sub-message definitions

### Composition Rules

1. **Every protocol needs**: variants + entity + shim + serdes (minimum viable model)
2. **Monitors are optional** but recommended for testing
3. **Modules are optional** -- only needed for reusable parameterized components
4. **Include chains** must be consistent -- no circular dependencies

### Using the Pattern Library

#### Adding patterns to a new protocol
```
/nct-add-pattern {protocol} all
```

#### Analyzing existing patterns
Use the `ivy_patterns` MCP tool:
```
ivy_patterns(protocol="quic", mode="analyze")
ivy_patterns(protocol="quic", mode="validate")
ivy_patterns(protocol="quic", mode="compare", reference_protocol="bgp")
```

Template files are in `protocol-testing/patterns/` with the registry in `pattern_catalog.yaml`.

## Integration

**Used by:**
- **methodology-reference** -- Layer decomposition in NCT/NACT/NSCT workflows
- **ivy-writing-guide** -- Ivy language reference for writing layers

**Related commands:**
- `/nct-scaffold type=protocol` -- Scaffolds from the 14-layer template
- `/nct-add-pattern` -- Add a pattern to an existing specification
