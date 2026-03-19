# NCT Workflow — Full 10-Step Detail

This reference provides the complete NCT workflow with code examples.
Loaded on demand by the nct-methodology skill.

### Step-to-Phase Mapping

| Orchestrator Phase | Steps | Summary |
|---|---|---|
| **EXPLORE** | 1-2 | Select protocol/RFC, extract requirements |
| **PLAN** | 3-5 | Decompose into 14-layer template, design type + stack layers |
| **WRITE** | 6-8 | Entity roles, behavioral constraints, test specs |
| **VERIFY** | 9 | `ivy_verify` + `ivy_compile` (target=test) |
| **FINALIZE** | 10 | Run against IUT via PANTHER |

## Step 1: Select Target Protocol and RFC

Identify the protocol to test and the RFC(s) defining it. Extract testable requirements (MUST, SHOULD, MAY statements per RFC 2119).

Use `ivy_extract_requirements` MCP tool to parse RFC text and produce a requirements manifest.

## Step 2: Decompose into 14 Formal Layers

Map RFC sections to the 14-layer template. Minimum viable set (7 layers):

1. Types -> Frames -> Packets -> Connection (core data flow)
2. Entity definitions -> Entity behavior -> Shims (participants)
3. Test specifications (verification)

Full 14-layer template:

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 1 | Types | `{prot}_types.ivy` | Identifiers, bit vectors, enumerations |
| 2 | Application | `{prot}_application.ivy` | Data transfer semantics |
| 3 | Security | `{prot}_security.ivy` | Key establishment, handshake |
| 4 | Frame/Message | `{prot}_frame.ivy` | PDU definitions |
| 5 | Packet | `{prot}_packet.ivy` | Wire-level structure |
| 6 | Protection | `{prot}_protection.ivy` | Encryption/decryption |
| 7 | Connection | `{prot}_connection.ivy` | Session lifecycle |
| 8 | Transport Params | `{prot}_transport_parameters.ivy` | Negotiable parameters |
| 9 | Error Handling | `{prot}_error_code.ivy` | Error taxonomy |
| 10 | Entity Defs | `ivy_{prot}_{role}.ivy` | Network participant instances |
| 11 | Entity Behavior | `ivy_{prot}_{role}_behavior.ivy` | FSM + before/after monitors |
| 12 | Shims | `{prot}_shim.ivy` | Formal model to implementation bridge |
| 13 | Serialization | `{prot}_ser.ivy`, `{prot}_deser.ivy` | Wire format encoding/decoding |
| 14 | Utilities | `byte_stream.ivy`, `file.ivy`, `time.ivy` | Common utilities |

**Dependency order**: Types(1) -> Error(9), Frame(4) -> Packet(5) -> Protection(6) -> Connection(7) -> Entities(10-12)

## Step 3: Write Type Definitions

Start with `{prot}_types.ivy` — the foundation layer defining identifiers, bit vectors, enumerations used throughout the model.

```ivy
type cid                                    # Uninterpreted type
type stream_kind = {unidir, bidir}          # Enumerated type
interpret bit -> bv[1]                      # Bitvector interpretation

relation conn_seen(C:cid)                   # Boolean predicate (state)
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num  # Stateful value
individual the_cid : cid                    # Constant
```

## Step 4: Build Core Protocol Stack

Progress through layers in dependency order:
- Frame/Message layer (`{prot}_frame.ivy`) — PDU definitions
- Packet layer (`{prot}_packet.ivy`) — wire-level structure
- Protection layer (`{prot}_protection.ivy`) — encryption/decryption
- Connection layer (`{prot}_connection.ivy`) — session lifecycle

## Step 5: Define Entity Roles

Create entity definitions for each protocol participant:
- `ivy_{prot}_client.ivy` — client instance
- `ivy_{prot}_server.ivy` — server instance
- Optionally: MIM, attacker roles

## Step 6: Write Behavioral Constraints

Encode RFC requirements as before/after monitors in `ivy_{prot}_{role}_behavior.ivy`. This is the largest and most complex protocol-specific code.

```ivy
# Before: guard preconditions
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
    require pkt.hdr.version = negotiated_version;  # [rfc9000:4.1]
}
```

## Step 7: Create Test Specifications

Write role-specific test files with export declarations and _finalize:

```ivy
#lang ivy1.7
include order
include {prot}_infer
include file
include ivy_{prot}_shim_client
include ivy_{prot}_client_behavior

after init {
    # Initialize sockets, TLS, transport parameters
    sock := net.open(endpoint_id.client, client.ep);
    call tls_api.upper.create(0, false, extns);
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

**Variants** extend the base: `include {prot}_server_test` then add specific exports and weight attributes.

### Weight Attributes (test generation bias)
```ivy
attribute frame.stream.handle.weight = "10"       # Strongly prefer streams
attribute frame.rst_stream.handle.weight = "0.02"  # Rarely generate resets
```

## Step 8: Verify with ivy-tools

Use `ivy_diagnostics(mode="structural")` for fast structural check, then `ivy_verify` for formal property verification.
Check isolate assumptions, invariants, and safety properties.

## Step 9: Compile Test

Use `ivy_compile` with `target=test` to produce executable test binary.

## Step 10: Execute Against IUT

Run compiled test against the implementation via PANTHER experiment framework.

```bash
panther run --config experiment-config/base/experiment_config_example_minimal.yaml
```
