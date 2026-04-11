---
paths: ["**/*.ivy"]
---

## Ivy Language Patterns (from QUIC Reference Model)

### Types and State
```ivy
type cid                                    # Uninterpreted type
type stream_kind = {unidir, bidir}          # Enumerated type
interpret bit -> bv[1]                      # Bitvector interpretation

relation conn_seen(C:cid)                   # Boolean predicate (state)
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num  # Stateful value
individual the_cid : cid                    # Constant
```

### Before/After Monitor
```ivy
# Before: guard preconditions (from ivy_quic_client_server_behavior.ivy)
before frame.stream.handle(f:frame.stream, scid:cid, dcid:cid, e:quic_packet_type) {
    if _generating {
        require scid = the_cid;
        require connected(the_cid) & dcid = connected_to(the_cid);
        require f.length > 0;
    }
}

# After: state update + compliance check
after packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {
    conn_total_data(the_cid) := conn_total_data(the_cid) + pkt.payload_length;
    require pkt.hdr.version = negotiated_version;
}
```

### Object/Module Composition
```ivy
object quic_endpoint = {
    type this
    module client_ep(address:ip.addr, port:ip.port) = {
        variant this of quic_endpoint = struct { }
        individual ep : ip.endpoint
        after init { ep.protocol := ip.udp; ep.addr := address; ep.port := port; }
    }
}
```

### State Machine (Boolean FSM)
```ivy
relation sending_ready(S:stream_id)       # Stream created
relation sending_send(S:stream_id)        # Data sent
relation sending_dataSent(S:stream_id)    # FIN sent

after init { sending_ready(S) := true; sending_send(S) := false; }

action handle_sending_send(id:stream_id) = {
    sending_ready(id) := false;
    sending_send(id) := true;
}
```

### Shim Bridge (formal → implementation)
```ivy
after packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {
    if _generating {
        var spkt := pkt_serdes.to_bytes(pkt);           # Serialize
        var ppkt := prot.encrypt(tls_id, rnum, spkt);   # Encrypt via C++
        call net.send(endpoint_to_pid(src), endpoint_to_socket(src), dst, pkts);
    }
}
```

### RFC Traceability Tags
```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
```

### Weight Attributes (test generation bias)
```ivy
attribute frame.stream.handle.weight = "10"       # Strongly prefer streams
attribute frame.rst_stream.handle.weight = "0.02"  # Rarely generate resets
```

## RFC-to-Ivy Mapping

| RFC 2119 Keyword | Ivy Construct | Example |
|---|---|---|
| MUST | `require` in before/after | `require pkt.version = negotiated_version;` |
| MUST NOT | `require ~(condition)` | `require ~(f.offset > max_stream_data(f.id));` |
| SHOULD | Weaker assertion or warning | Optional: log but don't block |
| MAY | No assertion | Test correct handling when present |

**Connection close on violation**: `require connection_error(the_cid) = transport_parameter_error;`

## Test Specification Template

```ivy
#lang ivy1.7
include order                              # Standard library
include {prot}_infer                       # Type inference helpers
include ivy_{prot}_shim_{role}             # Shim for the role Ivy plays
include ivy_{prot}_{role}_behavior         # Behavioral constraints (monitors)

after init {                               # Socket + TLS/security setup
    sock := net.open(endpoint_id.{role}, {role}.ep);
    call tls_api.upper.create(0, false, extns);
}

export frame.ack.handle                    # Test mirror generates these actions
export frame.stream.handle
export packet_event

export action _finalize = {                # End-state verification
    require is_no_error;
    require conn_total_data(the_cid) > 0;
}
```

**Variants** extend the base: `include {prot}_server_test` then add exports and weight attributes.
