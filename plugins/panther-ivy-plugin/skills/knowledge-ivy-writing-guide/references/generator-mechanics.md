# Generator Mechanics -- Z3 Test Generation & Common Pitfalls

## Z3 Constraint Scope

Z3 solves for **exported action parameters** only. State variables (`function` and `relation` declarations) are fixed at their current value during each generation attempt. A `require` on a state variable is a pass/fail gate: if the current value does not satisfy the constraint, the attempt is rejected. Z3 cannot "force" state variables to new values.

Consequence: any message context that the solver needs to choose must be an action parameter, not state.

<anti_pattern>
```ivy
# WRONG -- e is a state variable, Z3 cannot solve for it
object path_attr = {
    object origin = {
        # msg_type is a relation/function on the object
        function current_type : bgp_message_type

        action handle(src:ip.endpoint, dst:ip.endpoint) = {
            require current_type = bgp_message_type.update;  # gate, not solvable
            ...
        }
    }
}
```
</anti_pattern>

<example>
```ivy
# CORRECT -- e is a parameter, Z3 can solve for it
object path_attr = {
    object origin = {
        action handle(src:ip.endpoint, dst:ip.endpoint, e:bgp_message_type) = {
            require e = bgp_message_type.update;  # Z3 picks e = update
            ...
        }
    }
}
```
</example>

QUIC uses the same pattern: `frame.*.handle` takes `e:quic_packet_type` as a parameter so Z3 can solve `require e = quic_packet_type.initial`.

**Rule**: if a `require` constrains a value that the generator must choose, that value must be an action parameter.

---

## Generator Starvation

**Definition**: the generator runs thousands of iterations but produces few or no protocol messages on the wire.

**Symptoms**:
- High iteration count in Ivy logs, few messages in pcap
- IUT hold timer expires or session never establishes
- `_finalize` fails due to zero data transferred

### Causes

1. **Timer event competition**: exported timer events (`hold_timer_expired`, `keepalive_timer_expired`) compete with message events for selection. Timer events that set `conn_state` to `idle` kill the session in one shot. Message events need successful parameter generation to produce output. With N exported events, each has roughly 1/N selection probability, and timer kills are instant while message sends may require satisfiable constraints.

2. **Two-step message pattern**: if sending a message requires two consecutive event picks (e.g., first pick `update_event`, then pick `header_event`), the probability of the correct sequence drops to 1/N^2. This compounds with cause 1.

3. **Unsatisfiable requires**: handle actions with `require` on state variables that are never in the right state at generation time. The attempt is silently rejected and the iteration is wasted.

4. **Missing exports**: composite messages need all sub-element handle actions exported. If `path_attr.origin.handle` is not exported, the generator cannot build UPDATE messages containing ORIGIN attributes.

### Diagnostic Checklist

- Count exported events (`export` declarations in test file). Fewer is better for throughput.
- Cross-validate Ivy logs against pcap. Events logged by Ivy do not always produce wire transmission.
- Check whether timer events are in the export list. Consider removing them or using weight attributes to suppress.
- Check for two-step send patterns. Refactor to single-event auto-send (see next section).

---

## Auto-Send Pattern

For IUT testing, each message event's `after` block should serialize, wrap in a header, send on the wire, and reset state atomically within a single event pick. This is the **auto-send pattern**.

### Correct Pattern (BGP)

<example>
```ivy
action send_wrapped_message(src:ip.endpoint, dst:ip.endpoint) = {
    if _generating {
        # 1. Serialize the message body already built by handle actions
        var data := bgp_ser.serialize_message(msg_body);
        # 2. Wrap in BGP header (type + length)
        var pkt := bgp_header.wrap(bgp_message_type.update, data);
        # 3. Send on wire
        call net.send(src, dst, pkt);
        # 4. Reset builder state for next message
        call reset_message_state;
    }
}
```
</example>

The `if _generating` guard ensures this only fires during test generation, not during IUT message processing.

### Anti-Pattern (Two-Step)

<anti_pattern>
```ivy
# BAD -- requires two consecutive picks: first pick message event, then pick header event
export message_event       # pick 1: builds message body
export header_send_event   # pick 2: wraps and sends

# Probability of correct sequence: 1/N * 1/N = 1/N^2
# With 10 exported events, only 1% chance per pair of iterations
```
</anti_pattern>

### Gold Standard (QUIC)

QUIC's `packet_event` after-block is the reference implementation. It frames, encrypts, and sends in a single exported action. All frame handle actions (`frame.stream.handle`, `frame.ack.handle`, etc.) build frame content, and `packet_event` atomically wraps and transmits.

---

## Handle Action Guards

When exporting handle actions (sub-element builders like `path_attr.origin.handle` or `frame.crypto.handle`), add `before` blocks with `_generating` guards. Without these guards, Z3 picks arbitrary endpoint values and corrupts per-speaker state.

### Required Guards

```ivy
# BGP example
before path_attr.origin.handle(src:ip.endpoint, dst:ip.endpoint, e:bgp_message_type) {
    if _generating {
        require src = speaker.ep;           # constrain to our speaker
        require dst = peer.ep;              # constrain to the peer
        require e = bgp_message_type.update; # constrain message context
    }
}
```

Without the `src`/`dst` guards, the generator may pick `src = peer.ep` and `dst = speaker.ep` (reversed), causing the handle action to modify the peer's state instead of the speaker's state. This silently corrupts the model and produces nonsensical wire output.

### QUIC Equivalent

```ivy
before frame.crypto.handle(f:frame.crypto, scid:cid, dcid:cid, e:quic_packet_type) {
    if _generating {
        require scid = the_cid;
        require dcid = server_cid;
        require e = quic_packet_type.initial;
    }
}
```

### Rules

1. Every exported handle action needs a `before` block with `_generating` guard.
2. Constrain `src`/`dst` (or `scid`/`dcid`) to the correct connection endpoints.
3. Constrain the message type parameter `e` to the correct context.
4. Place guards in the test file, not in the protocol model (they are test-specific).
