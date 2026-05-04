---
name: specification-patterns
description: "Use when designing layer structure or scaffolding a new protocol model. Provides the 14-layer template reference and the formal-model pattern scaffolding guide."
user-invocable: false
---

# Specification Patterns: Formal Model Pattern Library

**Type:** flexible — adapt principles to context.

**Journal:** read-only knowledge skill. Per `.claude/rules/journaling-contract.md` §1, this skill does NOT write to `.panther-ivy/workflow-journal.yaml`; the orchestrator and the 5 ops-skills are the writer surfaces.

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill owns *layer-decomposition* decisions (which file does a type belong in, which layer depends on which) and the formal model pattern library. `ivy-syntax` owns *language-level* decisions (how to write a before/after monitor, what `around` means, how `require` interacts with `_generating`). Load both when designing a new layer; load only `ivy-syntax` when editing within a layer.

---

## 14-Layer template (canonical reference)

### Inline minimal-viable reference

A compact one-line-per-layer summary so cold-start sessions (no memory file present) have an immediate decomposition reference. The richer canonical content (decision matrices, optional layers, per-protocol directory templates) lives in the auto-memory file linked below.

| # | Layer | Purpose | Typical file |
|---|-------|---------|--------------|
| 1 | Types | Primitive types, opaque domains, type aliases (sequence numbers, identifiers, enums) | `<prot>_1_types.ivy` |
| 2 | Application | Protocol-level payload types (QUIC stream payload, BGP NLRI, CoAP option) | `<prot>_2_application.ivy` |
| 3 | Security | Cryptographic primitives, key schedule, AEAD / HMAC modules (when in scope) | `<prot>_3_security.ivy` |
| 4 | Frame | Per-PDU variant hierarchy (`frame.ivy` in QUIC; `message.ivy` in BGP) | `<prot>_4_frame.ivy` |
| 5 | Packet | Outer wire envelope (long / short header; BGP message envelope; CoAP header) | `<prot>_5_packet.ivy` |
| 6 | Protection | Header / body protection, AEAD wrap-unwrap, integrity (where layered on framing) | `<prot>_6_protection.ivy` |
| 7 | Connection | Session / connection state machine (open / established / closed) | `<prot>_7_connection.ivy` |
| 8 | Transport Params | Negotiated parameters, capabilities, hold-time / version / extensions | `<prot>_8_params.ivy` |
| 9 | Error | Error codes and error propagation actions | `<prot>_9_error.ivy` |
| 10 | Entity Defs | Roles (client / server / speaker / peer) and identity types | `<prot>_10_entity.ivy` |
| 11 | Entity Behavior | Per-role action wiring, before / after monitors, generated-event guards | `<prot>_11_behavior.ivy` |
| 12 | Shims | Socket I/O bridge between Ivy actions and the runtime network | `<prot>_shims/` |
| 13 | Serialization | Wire serdes (`ivy_binary_ser_*`) for variant types declared in layer 4 | `<prot>_13_ser.ivy` |
| 14 | Utilities | Helpers shared across layers (logging, randomness, time) | `<prot>_utils.ivy` |

Layer numbering is canonical: lower numbers depend on nothing higher. When a protocol omits an optional concept (e.g., no protection for clear-text protocols), the layer number is left as a gap rather than renumbered, so cross-protocol comparison stays straightforward.

### Auto-memory authoritative source

The richer canonical reference lives in user auto-memory at `~/.claude/projects/<project>/memory/reference_nct_methodology.md`, mirrored by the `methodology` skill body. The auto-memory file additionally carries:

- Optional (protocol-dependent) layers — Security Sub-Protocol, FSM Modules, Recovery & Congestion, Extensions, Attacks Stack, Stream / Flow Management.
- Genuinely reusable components across protocols.
- Decision matrix for template selection (connection-oriented, built-in reliability, multiplexed streams, integrated security, peer-to-peer, pub/sub, extensions, stateless, tunneling, real-time).
- Minimal viable 7-layer set for a new protocol model.
- Per-protocol directory-structure template.

`Read` the memory file when designing a new protocol's layer structure or choosing optional layers. `references/pattern-library-detail.md` in this skill holds the expanded formal-model pattern library; `references/frame-queuing-pattern.md` covers the frame-queuing composition pattern. The inline table above is the cold-start fallback when the memory file is unreachable; it is not a substitute for the rich canonical reference.

---

## Formal Model Pattern Library

7 recurring patterns across PANTHER Ivy protocol models (QUIC, BGP, CoAP, MiniP). Load `references/pattern-library-detail.md` for full code examples and decision points.

### Pattern Overview

| # | Pattern | Layer | Purpose |
|---|---------|-------|---------|
| 1 | **Variants** | 4 | PDU type hierarchy (message/frame/packet) |
| 2 | **Modules** | 6 | Parameterized reusable components |
| 3 | **Entities** | 10 | Protocol participants (client/server/speaker) |
| 4 | **Monitors** | 11 | Behavioral constraints (before/after) |
| 5 | **Shims** | 12 | Network I/O bridge (socket layer) |
| 6 | **Serdes** | 13 | Wire-format serialization/deserialization |
| 7 | **Include Chain** | all | Layer composition via include ordering |

### Pattern Dependencies and Scaffolding Order

```
variants (no deps)
  +-- serdes (needs variant tags for state machine)
  +-- monitors (constrain variant event actions)
entity (no deps)
module (no deps)
  +-- shim (bridges entities + serdes to network)
```

**Scaffolding order**: variants -> entity -> module -> serdes -> monitors -> shim. See `references/pattern-library-detail.md` for composition rules and detailed patterns; see `references/frame-queuing-pattern.md` for the frame-queuing composition pattern (composite protocol messages with sub-element arrays).

## Integration

- **LOADED BY:** scaffold workflow (plan phase)

**Related skills:**
- **methodology** -- Layer decomposition in NCT/NACT/NSCT workflows
- **ivy-syntax** -- Ivy language reference for writing layers
- **ivy-toolkit** -- MCP tool parameters for pattern analysis

**Related agents:**
- **ivy-refiner-agent** -- Compile-error diagnosis and verification across layers

**Related workflows:**
- **build** -- Scaffolds from the 14-layer template and adds patterns interactively
