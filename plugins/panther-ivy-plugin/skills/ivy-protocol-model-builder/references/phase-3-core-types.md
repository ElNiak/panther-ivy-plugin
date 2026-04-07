# Phase 3: Core Types and Stack

## Purpose

Write the first compilable `.ivy` files: types, message structures, state tracking.

## Ivy Concepts Taught

- **Scalar types**: `type query_id` (abstract), `interpret query_id -> bv[16]` (bit-vector interpretation for compilation)
- **Bit-vector sizing**: Choose width to match the field's wire format width. If variable-length, choose a width large enough for the maximum value needed in testing. E.g., a 16-bit DNS query ID uses `bv[16]`, a 4-bit QUIC CID length uses `bv[4]`.
- **Enumerations**: `type rcode = {noerror, formerr, servfail, nxdomain}`
- **Aliases**: `alias aid = cid` — creates a type alias (used in `quic_types.ivy:43`)
- **Definitions**: `definition zero = 0` — named constants
- **Structs**: `type this = struct { field : type, ... }` inside an `object` block
- **`this` keyword**: Means "the enclosing object's type"
- **Arrays**: `instance idx : unbounded_sequence` + `instance arr : array(idx, this)`
- **Variants**: `variant this of base_type = struct { ... }` — declares a subtype of a base type. Ivy dispatches on variant types at runtime. Use for frame-like sub-types where one base type has multiple formats.
- **Relations**: `relation name(X:type)` — boolean predicates over typed parameters
- **Functions**: `function name(X:type) : return_type` — value mappings
- **`after init` blocks**: Initialize all relations to false, functions to defaults
- **Actions with empty bodies**: `action event_name(params) = {}` — behavior defined by advice elsewhere. These are placeholders; in Phase 5, attach behavior using `around` and `before` advice blocks.
- **Boolean operators**: `~` (not), `&` (and), `|` (or) — used in `require` expressions

## QUIC Model References

- Types: `quic_types.ivy` — `cid`, `pkt_num`, `version`, `quic_packet_type` enum, `alias aid = cid`
- Structs: `quic_packet.ivy:94-102` — `quic_packet` struct with fields: `ptype`, `pversion`, `dst_cid`, `src_cid`, `token`, `seq_num`, `payload`
- Variants: `quic_frame.ivy:47-83` — `frame.ping`, `frame.ack` as variants of `frame`
- State: `quic_packet.ivy:229-329` — `conn_seen`, `sent_pkt`, `last_pkt_num`, `connected`, etc., with `after init` block
- Aggregator: `quic_connection.ivy` — includes all stack files in dependency order
- Actions: `quic_packet.ivy:137` — `action packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) = {}`

## Build Order

1. **Types file** — scalars, enums, aliases, bit-vector interpretations. No dependencies. Verify with `ivy_verify` MCP tool.
2. **Message struct file** — struct definitions, array instances, main event action. Includes types.
3. **Sub-message types** (if variants needed) — frame-like sub-structures. Skip for single-message protocols.
4. **State tracking file** — relations, functions, `after init` block. Includes types.
5. **Aggregator file** — includes all stack files in correct order. Single entry point for the shim layer.

## What This Phase Does NOT Do

No `around`/`require` specifications. No entity definitions. No serialization. The stack defines the data model and declares events with empty bodies. Specification logic comes in Phase 5.

For Ivy syntax details beyond this tutorial, consult the `ivy-writing-guide` skill.

## Checkpoint

Run `ivy_verify` MCP tool on the aggregator file (or `ivy_check {proto}_connection.ivy` CLI). Expected output: no errors.

Common errors at this stage:
- **"sort mismatch"**: Type error — check field types in structs match declared types.
- **"cannot find module"**: Include path wrong — Ivy resolves includes relative to the working directory.
- **"multiple definitions"**: Name collision — two included files define the same name.

Run `ivy_diagnostics(mode="structural")` after each file for fast feedback.

---

**STOP.** Present all files and verification results to the user. Do NOT proceed until user confirms type mappings match the RFC.
