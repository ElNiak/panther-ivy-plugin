---
name: pattern-library
description: Use when choosing or composing formal model patterns (variants, serdes, shims, monitors, entities, modules) for a protocol specification
---

# Formal Model Pattern Library

This skill documents the 7 recurring patterns found across PANTHER Ivy protocol models (QUIC, BGP, CoAP, MiniP). Use these patterns when creating new protocol specifications.

## Pattern Overview

| # | Pattern | Layer | Purpose | Example Protocol |
|---|---------|-------|---------|-----------------|
| 1 | **Variants** | 4 | PDU type hierarchy (message/frame/packet) | BGP messages, QUIC frames |
| 2 | **Modules** | 6 | Parameterized reusable components | QUIC protection, crypto |
| 3 | **Entities** | 10 | Protocol participants (client/server/speaker) | MiniP endpoints, BGP speakers |
| 4 | **Monitors** | 11 | Behavioral constraints (before/after) | BGP speaker behavior |
| 5 | **Shims** | 12 | Network I/O bridge (socket layer) | MiniP UDP shim, BGP TCP shim |
| 6 | **Serdes** | 13 | Wire-format serialization/deserialization | MiniP ping_ser, BGP bgp_ser |
| 7 | **Include Chain** | all | Layer composition via include ordering | All protocols |

## Pattern Dependencies

```
variants (no deps)
  └─→ serdes (needs variant tags for state machine)
  └─→ monitors (constrain variant event actions)
entity (no deps)
module (no deps)
  └─→ shim (bridges entities + serdes to network)
```

**Scaffolding order**: variants → entity → module → serdes → monitors → shim

## 1. Variants Pattern

**Purpose**: Define PDU (Protocol Data Unit) type hierarchies — the messages, frames, or packets your protocol exchanges.

**When to use**: Every protocol needs this. It's the foundational data model.

**Decision points**:
- **Struct fields**: What fields does each message type have? (header fields, payload, type discriminator)
- **Dispatch method**: How are sub-types identified? (type field, first byte, TLV)
- **Nesting**: Does a message contain sub-messages? (e.g., BGP UPDATE contains path_attrs)

**Template**: `patterns/variants/variant_frame_template.ivy`

**Cross-protocol examples**:
- **BGP**: `bgp_header_message` with `bgp_type` discriminator → dispatches to open/update/notification/keepalive
- **QUIC**: `quic_frame` with frame type byte → dispatches to stream/ack/crypto/etc.
- **MiniP**: `ping_packet` with simple frame type → ping/pong/time

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
        # Dispatch by type
        if msg.msg_type = {prot}_message_type.type_a {
            var sub := {prot}_type_a_serdes.from_bytes(msg.payload);
            call {prot}_type_a_event(src, dst, sub);
        } else if msg.msg_type = {prot}_message_type.type_b {
            ...
        }
    }
}
```

## 2. Modules Pattern

**Purpose**: Parameterized, reusable protocol components that can be instantiated with different types.

**When to use**: When you have a component that works with different type parameters (e.g., protection/crypto that works with different TLS configurations).

**Decision points**:
- **Type parameters**: What types should be parameterized?
- **Internal state**: What instances/arrays does the module need?
- **Inline C++**: Does performance-critical code need embedded C++?

**Template**: `patterns/modules/parameterized_module_template.ivy`

**Cross-protocol example**:
- **QUIC**: `quic_protection(tls_id, tls)` — packet encryption/decryption parameterized by TLS type

## 3. Entities Pattern

**Purpose**: Define protocol participants — the endpoints that send and receive messages.

**When to use**: Every protocol needs at least one entity type.

**Decision: Asymmetric vs Symmetric**:
- **Asymmetric** (client/server): Different roles have different behavior (e.g., MiniP ping client sends pings, server sends pongs). Use `entity_role_pair_template.ivy`.
- **Symmetric** (speaker/peer): Both sides use the same behavior (e.g., BGP speakers). Use `entity_symmetric_template.ivy`.

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
        action behavior(...) = { ... }
    }
}
```

## 4. Monitors Pattern

**Purpose**: Constrain action behavior with before/after/around blocks. This is where protocol requirements are formally specified.

**When to use**: For every action that generates or processes protocol messages.

**Decision points**:
- **`if _generating` guard**: Use in `before` blocks to constrain test traffic generation (Ivy acts as the tester)
- **Which actions to monitor**: Start with the top-level message event, then add per-sub-message monitors
- **Field constraints**: What values must fields have? (protocol version, message lengths, markers)

**Templates**:
- `monitors/before_after_template.ivy` — Main behavioral constraints
- `monitors/finalize_template.ivy` — End-of-test assertions
- `monitors/export_weight_template.ivy` — Test exports with generation weights

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

## 5. Shims Pattern

**Purpose**: Bridge between the formal specification and real network I/O. Routes received packets to entity behaviors and serializes generated messages for sending.

**When to use**: Required for any protocol that runs over a real network (UDP/TCP).

**Decision: UDP vs TCP**:
- **UDP**: Stateless, simpler. Use `shim_udp_template.ivy`. (MiniP, CoAP, QUIC)
- **TCP**: Stateful (connection tracking with `isup`/`pend` relations). Use `shim_tcp_template.ivy`. (BGP, HTTP)

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

## 6. Serdes Pattern

**Purpose**: Serialize Ivy objects to wire bytes and deserialize wire bytes back to Ivy objects. Implemented as C++ state machines embedded in Ivy.

**When to use**: For any protocol that exchanges binary or text messages over a network.

**Decision: Binary vs JSON**:
- **Binary**: Fixed-width fields, tag-based encoding. Use `binary_ser_template.ivy`. (MiniP, BGP, QUIC)
- **JSON**: Text-based key-value encoding. Use `json_ser_template.ivy`. (Mark/MASFAD, REST APIs)

**Key structure**:
```ivy
object {prot}_ser = {}
<<< member
    class `{prot}_ser`;
>>>
<<< impl
    class `{prot}_ser` : public ivy_binary_ser_128 {
        enum { {prot}_s_init, {prot}_s_field1, ... } state;
        // State machine for serialization
    };
>>>
```

**Critical invariant**: Enum states in ser and deser must correspond to variant tags 1:1.

## 7. Include Chain Pattern

**Purpose**: Compose layers by including files in dependency order. Lower layers must be included before higher layers.

**Recommended include ordering**:
1. Type definitions (`{prot}_types`)
2. Application layer (`{prot}_application`)
3. Packet/frame definitions (`{prot}_packet`)
4. Utility includes (time, collections, ip, deserializer, serdes)
5. Ser/deser files
6. Entity definitions
7. Behavior specifications
8. Network/shim layer
9. Message dispatch
10. Sub-message definitions

## Composition Rules

1. **Every protocol needs**: variants + entity + shim + serdes (minimum viable model)
2. **Monitors are optional** but recommended for testing (they constrain test generation)
3. **Modules are optional** — only needed for reusable parameterized components
4. **Include chains** must be consistent — no circular dependencies

## Using the Pattern Library

### Adding patterns to a new protocol
```
/nct-add-pattern {protocol} all
```

### Adding a specific pattern
```
/nct-add-pattern {protocol} serdes --wire-format json
/nct-add-pattern {protocol} entity --role-type symmetric
```

### Analyzing existing patterns
Use the `ivy_pattern_analysis` MCP tool:
```
ivy_pattern_analysis(protocol="quic", mode="detect")
ivy_pattern_analysis(protocol="quic", mode="validate")
ivy_pattern_analysis(protocol="quic", mode="compare", reference_protocol="bgp")
```

### Template files location
All templates are in `protocol-testing/patterns/` with the registry in `pattern_catalog.yaml`.

## Integration

**Used by:**
- **panther-ivy:14-layer-template** — Patterns applied within layers
- **panther-ivy:nct-methodology** — Pattern selection during model building

**Related commands:**
- `/nct-add-pattern` — Add a pattern to an existing specification

**Related agents:**
- **ivy-model-reviewer** — Reviews pattern usage quality
