# Phase 4: Entity Model

## Purpose

Create endpoints that send/receive protocol messages and the shim bridges connecting the formal model to real network I/O.

## Ivy Concepts Taught

- **Modules**: `module client_ep(address:ip.addr, port:ip.port) = { ... }` — parameterized code templates
- **`instance`**: `instance server : endpoint.server_ep(addr, port)` — module instantiation with concrete values
- **`individual`**: Singleton values scoped to a module instance (like global variables)
- **`parameter`**: `parameter server_addr : ip.addr = 0x0a000001` — declares a value settable from the command line when the compiled binary runs. Every entity file uses this for IP addresses and ports at runtime.
- **`import action`**: `import action show_debug(msg:stream_data)` — declares an action implemented in C++ (not Ivy). Used for debug output and integration with native code. The QUIC model uses ~10 `import action show_*` declarations in `quic_packet.ivy` for observability.
- **The `ip` module**: Built-in panther_ivy infrastructure providing `ip.endpoint` (address + port + protocol), `ip.addr`, `ip.port`, and socket interfaces.
- **The `net` module**: `net.open`, `net.send`, `net.recv` — socket operations used in shims.
- **The `behavior` action**: The receive path that deserializes incoming UDP bytes into Ivy model events. This is the most complex part of the entity model. See detailed section below.

## The `behavior` Action (Detailed)

The `behavior` action bridges raw bytes to formal model events. In the QUIC model (`quic_entities_behavior/quic_endpoint.ivy:57`), it is ~200 lines that:
1. Receive a raw byte array from `net.recv`
2. Parse header bytes using bit manipulation (`bvand`, `bfe` for bit-field extraction)
3. Determine the message/packet type from header bits
4. Dispatch to the appropriate deserialization path
5. Call the formal model's event action (e.g., `packet_event`) with the deserialized struct

For a simpler protocol, `behavior` can be much shorter. A DNS-over-UDP model might have a 20-line `behavior` that reads a DNS header (12 bytes), extracts the query ID and flags, and calls `message_event`. The complexity scales with the protocol's wire format complexity.

Guide users through writing `behavior` incrementally: start with the simplest message type, get it parsing correctly, then add dispatch for additional types.

## QUIC Model References

- Endpoint module: `quic_entities_behavior/quic_endpoint.ivy:27-80` — `client_ep` module with socket setup and `behavior` action
- Entity file: `quic_entities/ivy_quic_server.ivy` — declares `parameter server_addr`, instantiates `quic_endpoint.server_ep(server_addr, server_port)`
- Base shim: `quic_shims/quic_shim.ivy` — central composition point including stack aggregator, all entity files, serialization (19 includes total), attack connection, TLS messages, locale
- Role shim: `quic_shims/ivy_quic_shim_server.ivy:39-56` — `after packet_event` serializes outgoing packets and calls `net.send`. Note: role shims use `after` advice (not `around`) because they add side effects (sending), not preconditions.

## Entity Pattern (Three Layers Per Role)

1. **Endpoint module** (`{proto}_entities_behavior/{proto}_endpoint.ivy`): Parameterized module with `individual` socket, `after init` setup, `behavior` action for the receive path.
2. **Entity file** (`{proto}_entities/ivy_{proto}_{role}.ivy`): Declares `parameter` values (address, port), instantiates endpoint module, includes the shim.
3. **Shim file** (`{proto}_shims/ivy_{proto}_shim_{role}.ivy`): Implements `after message_event` for serialize+send, delegates incoming bytes to `behavior` for deserialize.

## Adaptation by Protocol Shape

| Shape | Entity Pattern |
|---|---|
| Client-server | Asymmetric: separate client_ep and server_ep modules |
| P2P | Symmetric: single peer_ep module, instantiated multiple times |
| Stateless | Simplified behavior action: no connection tracking, just message parse |
| Layered on QUIC | Shim reads from QUIC streams instead of raw UDP sockets |
| Mid-connection format change | behavior action uses packet type dispatch (if/else on header bits) |

## Serialization Strategy

Two approaches:
- **Pass-through** (for early prototyping): Skip ser/deser, pass Ivy structs directly. Works for `ivy_verify` but not runnable tests.
- **Full ser/deser** (for real implementation testing): Field-by-field byte packing/unpacking in `{proto}_utils/{proto}_ser.ivy` and `{proto}_deser.ivy`. Protocol-specific, maps to wire format.

Start with pass-through, validate the model logically through Phase 5, then implement full ser/deser before Phase 6's integration tests against real implementations. The transition point is explicit: Phase 5 step 5 ("Integration test") requires full ser/deser. If only doing model validation (no real implementation testing), pass-through is sufficient for all phases.

## Build Order

1. **Endpoint module** — parameterized modules per role, `individual` declarations, `after init`.
2. **Entity files** — one per role, `parameter` declarations, instantiate endpoint modules.
3. **Base shim** — central composition point: includes stack aggregator, all entity files, serialization modules, locale, and (if crypto) protection module.
4. **Role-specific shims** — `after message_event` for outgoing (serialize + `net.send`), receive callback delegates to `behavior` for incoming.
5. **Serialization** (if targeting real impl testing) — `{proto}_ser.ivy` and `{proto}_deser.ivy` in `{proto}_utils/`.

## Checkpoint

Run `ivy_compile(target="test")` MCP tool (or `ivyc target=test {proto}_{role}_test.ivy` CLI) on a minimal test file that includes the shim and exports one action. The binary should compile. Invoke it with:

```bash
./{proto}_{role}_test seed=1 server_addr=0x7f000001 server_port=4443 client_addr=0x7f000001 client_port=4987
```

It will start and immediately terminate (no meaningful behavior yet). Success means compilation works.

---

**STOP.** Present compilation result to the user. Do NOT proceed until user reviews entity architecture and shim wiring.
