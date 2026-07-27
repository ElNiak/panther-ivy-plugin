# Formal Model Pattern Library — Full Reference

This document contains the detailed formal model pattern library extracted from the `specification-patterns` skill. It documents the 7 recurring patterns found across PANTHER Ivy protocol models (QUIC, BGP, CoAP, MiniP), including code examples, decision points, and composition rules.

---

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
  +-- serdes (needs variant tags for state machine)
  +-- monitors (constrain variant event actions)
entity (no deps)
module (no deps)
  +-- shim (bridges entities + serdes to network)
```

**Scaffolding order**: variants -> entity -> module -> serdes -> monitors -> shim

---

## 1. Variants Pattern

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

---

## 2. Modules Pattern

**Purpose**: Parameterized, reusable protocol components that can be instantiated with different types.

**When to use**: When you have a component that works with different type parameters.

**Cross-protocol example**: QUIC `quic_protection(tls_id, tls)` -- packet encryption/decryption parameterized by TLS type.

---

## 3. Entities Pattern

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

---

## 4. Monitors Pattern

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

---

## 5. Shims Pattern

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

---

## 6. Serdes Pattern

**Purpose**: Serialize Ivy objects to wire bytes and deserialize wire bytes back to Ivy objects.

**Decision: Binary vs JSON**:
- **Binary**: Fixed-width fields, tag-based encoding. (MiniP, BGP, QUIC)
- **JSON**: Text-based key-value encoding. (REST APIs)

**Critical invariant**: Enum states in ser and deser must correspond to variant tags 1:1.

---

## 7. Include Chain Pattern

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

---

## Composition Rules

1. **Every protocol needs**: variants + entity + shim + serdes (minimum viable model)
2. **Monitors are optional** but recommended for testing
3. **Modules are optional** -- only needed for reusable parameterized components
4. **Include chains** must be consistent -- no circular dependencies

## Using the Pattern Library

### Adding patterns to a new protocol
```
ivy_patterns(mode="scaffold", protocol="{protocol}", pattern="all")
```

### Analyzing existing patterns
Use the `ivy_patterns` MCP tool:
```
ivy_patterns(mode="analyze", protocol="quic")
ivy_patterns(mode="validate", protocol="quic")
ivy_patterns(mode="compare", protocol="quic", reference_protocol="bgp")
```

Template files are in `protocol-testing/patterns/` with the registry in `pattern_catalog.yaml`.
