# Frame-Queuing Composition Pattern

## Purpose

Build composite protocol messages (messages containing variable-length lists of sub-elements) in a way that the Ivy test generator can produce them efficiently.

## When to Use

The protocol has messages with embedded sub-element arrays:
- QUIC: packets contain frames (CRYPTO, STREAM, ACK, etc.)
- BGP: UPDATE messages contain path attributes (ORIGIN, AS_PATH, NEXT_HOP, etc.)
- CoAP: messages contain options

## Architecture

Four components:

1. **Per-connection queue**: A state array that accumulates sub-elements
   - QUIC: `function queued_frames(C:cid) : frame.arr`
   - BGP: `function queued_path_attr(C:bgp_id) : path_attr.arr`

2. **Exported handle actions**: One per sub-element type, each validates and enqueues
   - QUIC: `export frame.ack.handle`, `export frame.crypto.handle`
   - BGP: `export path_attr.origin.handle`, `export path_attr.as_path.handle`
   - Each handle has an `around` block with `require` constraints and calls `enqueue_*()`

3. **Message event**: Exported action that consumes the queue
   - QUIC: `export packet_event` with `require pkt.payload = queued_frames(scid)`
   - BGP: `export bgp_update_message_event` with `require bgp_message.path_attrs = queued_path_attr(src)`
   - After consuming, clears the queue

4. **Generation guards**: `before` blocks constraining handle parameters during generation
   - src/dst must be the tester's speaker ID
   - Message type parameter must match the message context

## Generator Sequence

The random generator naturally produces:
```
handle -> handle -> handle -> message_event
```

Each handle is individually simple for Z3 (flag bools, simple field constraints). The message event just binds the pre-built queue to the payload.

## Key Design Rules

1. Pass message context as a PARAMETER (e.g., `e:bgp_message_type`), not via global state. Z3 can solve for parameters but not state variables.

2. Handle actions must have `_generating` guards constraining src/dst to the tester's speaker. Without this, Z3 picks arbitrary values and corrupts per-speaker state.

3. The message event should auto-send (serialize + send on wire atomically in the after-block). Do not require a separate header event.

4. Use `.end = 0` instead of `= arr.empty` for empty array constraints. Z3 handles integer equality better than array equality.

## Anti-Patterns

- NOT exporting handle actions: makes composite messages ungeneratable (the queue is never populated)
- Requiring state variables in handles without setting them: `require header_type = update_mess` fails if header_type was never set
- Exporting timer events alongside handle/message events: timers compete and can kill sessions

## File References

- QUIC frame queuing: `protocol-testing/quic/quic_stack/quic_frame.ivy` (enqueue_frame, lines ~2008-2036)
- QUIC packet binding: `protocol-testing/quic/quic_stack/quic_packet.ivy` (packet_event around, lines ~561-582)
- BGP path attr queuing: `protocol-testing/bgp/bgp_stack/bgp_path_attribute.ivy` (enqueue_path_attr)
- BGP UPDATE binding: `protocol-testing/bgp/bgp_stack/bgp_update_message.ivy` (around bgp_update_message_event)
- BGP handle guards: `protocol-testing/bgp/bgp_entities/ivy_bgp_speaker_behavior.ivy` (before path_attr.*.handle)
