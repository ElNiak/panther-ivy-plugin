# Ivy 1.7 Language Patterns Reference

Canonical Ivy 1.7 syntax reference: types, actions, invariants, before/after monitors, objects, modules, isolates, FSM shapes, RFC-to-Ivy mapping, test spec template, generator patterns, anti-patterns. Ships with the plugin so auto-loading on `.ivy` edits resolves locally without depending on any user-level auto-memory.

## File Header

Every Ivy file's first line is the language version pragma. PANTHER standardizes on Ivy 1.7.

```ivy
#lang ivy1.7
```

## Built-in Types

`bool`, `nat` (natural numbers), `int` (integers), `bv[N]` (bitvectors of width N).

## Types and State

```ivy
type cid                                    # Uninterpreted type
type stream_kind = {unidir, bidir}          # Enumerated type
interpret bit -> bv[1]                      # Bitvector interpretation

relation conn_seen(C:cid)                   # Boolean predicate (state)
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num  # Stateful value
individual the_cid : cid                    # Constant
```

## Action Body Semantics

Actions model state transitions. Four body-level keywords:

- `require` — precondition that must hold when the action fires. Under `_generating`, `require` acts as a generator constraint.
- `ensure` — postcondition that must hold after the body runs.
- `:=` — deterministic assignment to a relation, function, or individual.
- `assume` — introduces an assumption. Weakens the model soundness; use only when the assumption is externally guaranteed.

```ivy
action send(src: node_id, dst: node_id, p: packet_id) = {
    require connected(src, dst);
    require ~sent(p, dst);
    sent(p, dst) := true;
    ensure sent(p, dst)
}
```

## Invariants

Properties that must hold in every reachable state. Ivy checks them inductively: the invariant must hold initially (after `after init`) and be preserved by every action.

```ivy
invariant sent(P, N) -> connected(source(P), N)
invariant ack_pending(P) -> sent(P, dest(P))
```

Variables in an invariant are implicitly universally quantified. `invariant sent(P, N)` means "for all P, N, sent(P, N) is true" — rarely what the author intends. Bind via implication or a conditional form.

## Axioms and Conjectures

```ivy
axiom connected(X, Y) -> connected(Y, X)                  # Assumed true (not checked)
conjecture forall P. sent(P, dest(P)) -> ack_pending(P)   # Checked but not inductive
```

Axioms are unverified assumptions — minimise their use, because they weaken model soundness. Conjectures are checked by the verifier but are not used inductively in proofs.

## Before/After Monitor

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

## Object System

Objects group types, state, and actions under a namespace. `type this` declares the object's own self-type; nested objects compose namespaces.

```ivy
object frame = {
    type id
    relation valid(F: id)
    action create : id
    action destroy(f: id)
}
```

Inside an object, `type this` declares the object itself as a parameterised type. Instances of the object type can then be created and passed as action parameters:

```ivy
object counter = {
    type this
    individual val(X: this) : nat
    action increment(c: this) = { val(c) := val(c) + 1 }
}
```

### Nested Objects

Nested objects create hierarchical namespaces. Cross-references between nested siblings use dotted names.

```ivy
object protocol = {
    object client = {
        action connect(srv: server.endpoint)
    }
    object server = {
        type endpoint
        action accept(c: client)
    }
}
```

## Module System

Parameterized modules produce reusable type-polymorphic components.

```ivy
module ordered_set(elem) = {
    type this
    relation contains(S: this, E: elem)
    action add(s: this, e: elem) returns (s2: this)
}

instance packet_set : ordered_set(packet_id)
instance node_set : ordered_set(node_id)
```

## Isolates

Isolates define verification boundaries that separate specification from implementation. Each isolate is verified independently; other isolates are abstracted via their `specification` block.

```ivy
isolate protocol_spec = {
    object client = { ... }
    object server = { ... }
    specification { invariant ... }
}
```

## Include Directives

Includes search the Ivy standard library (`ivy/include/1.7`) and the current workspace include path. The directive omits the `.ivy` extension.

```ivy
include collections
include order
include my_protocol_types
```

Ivy does not support circular includes.

## Object/Module Composition

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

## Client/Server Roles

Entity roles are typically modelled as two sibling objects with complementary state:

```ivy
object client = {
    individual id : node_id
    relation connected
    after init { connected := false }
    action send_syn(srv: node_id) = {
        require ~connected;
    }
}

object server = {
    individual id : node_id
    relation listening
    after init { listening := true }
    action handle_syn(c: node_id) = {
        require listening;
    }
}
```

## State Machine (Boolean FSM)

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

## State Machine (Enum-valued)

An alternative, single-valued state pattern using an enumerated type. Prefer this when states are mutually exclusive and the FSM is small; prefer the boolean-relation form above when states can be concurrent or parameterized by an identifier.

```ivy
type conn_state = {idle, connecting, established, closing, closed}
individual state : conn_state
after init { state := idle }

action open_connection = {
    require state = idle;
    state := connecting
}

invariant state = established -> server.has_client(client.id)
```

## Packet Type Enum Pattern

Common shape for a wire-level packet object that carries a variant tag and addressing / sequencing fields.

```ivy
type packet_type = {handshake, data_pkt, control, close}
object packet = {
    type this
    function ptype(P: this) : packet_type
    function src(P: this) : node_id
    function dst(P: this) : node_id
    function seq(P: this) : nat
}
```

## Shim Bridge (formal → implementation)

```ivy
after packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {
    if _generating {
        var spkt := pkt_serdes.to_bytes(pkt);           # Serialize
        var ppkt := prot.encrypt(tls_id, rnum, spkt);   # Encrypt via C++
        call net.send(endpoint_to_pid(src), endpoint_to_socket(src), dst, pkts);
    }
}
```

## RFC Traceability Tags

```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
```

## Weight Attributes (test generation bias)

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

<example>
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
</example>

**Variants** extend the base: `include {prot}_server_test` then add exports and weight attributes.

## Generator Patterns (Test Traffic Generation)

### Auto-send pattern

Merge message construction and sending into one exported action so every generator selection produces a wire message:

<example>
```ivy
after msg_event(src:ip.endpoint, dst:ip.endpoint, msg:protocol_message) {
    if _generating {
        call net.send(endpoint_to_pid(src), endpoint_to_socket(src), dst, msg_serdes.to_bytes(msg));
    }
}
```
</example>

### Handle action `_generating` guard

Export handle actions for composite message sub-elements with a generating guard:

<example>
```ivy
export frame.path_attribute.handle
before frame.path_attribute.handle(f:frame.path_attribute, scid:bgp_id) {
    if _generating { require connected(the_cid); require scid = the_cid; }
}
```
</example>

### Anti-patterns

<anti_pattern>
- **Two-step message events**: Splitting message construction and sending into separate exported actions (e.g., `build_update` + `send_update`). The generator must pick both in sequence by chance, causing starvation. Merge into a single action.
- **Timer event exports**: Exporting `timeout_event` or `keepalive_timer` lets the generator waste iterations on non-message actions. Remove timer exports from test files; handle timers internally via shim callbacks or `after init`.
</anti_pattern>
