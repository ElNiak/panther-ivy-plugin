---
name: knowledge-specification-patterns
description: "Use when designing layer structure or scaffolding a new protocol model. Provides the 14-layer template reference and the formal-model pattern scaffolding guide."
user-invocable: false
---

# Specification Patterns: Formal Model Pattern Library

**Type:** flexible — adapt principles to context.

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill owns *layer-decomposition* decisions (which file does a type belong in, which layer depends on which) and the formal model pattern library. `ivy-writing-guide` owns *language-level* decisions (how to write a before/after monitor, what `around` means, how `require` interacts with `_generating`). Load both when designing a new layer; load only `ivy-writing-guide` when editing within a layer.

---

## 14-Layer template (canonical reference)

The 14-layer formal model template (Types / Application / Security / Frame / Packet / Protection / Connection / Transport Params / Error / Entity Defs / Entity Behavior / Shims / Serialization / Utilities) lives canonically in user auto-memory; see `.claude/rules/nct-methodology.md` for the path. This skill does not restate the table.

The memory file also carries:

- Optional (protocol-dependent) layers — Security Sub-Protocol, FSM Modules, Recovery & Congestion, Extensions, Attacks Stack, Stream/Flow Management.
- Genuinely reusable components across protocols.
- Decision matrix for template selection (connection-oriented, built-in reliability, multiplexed streams, integrated security, peer-to-peer, pub/sub, extensions, stateless, tunneling, real-time).
- Minimal viable 7-layer set for a new protocol model.
- Per-protocol directory-structure template.

`Read` the memory file when designing a new protocol's layer structure or choosing optional layers. `references/pattern-library-detail.md` in this skill holds the expanded formal-model pattern library; `references/frame-queuing-pattern.md` covers the frame-queuing composition pattern.

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

**Scaffolding order**: variants -> entity -> module -> serdes -> monitors -> shim

Load `references/pattern-library-detail.md` for composition rules and detailed patterns.

## Reference Files

Load `references/frame-queuing-pattern.md` for the frame-queuing composition pattern (building composite protocol messages with sub-element arrays).

## Integration

- **LOADED BY:** build workflow (plan phase)

**Related skills:**
- **methodology-reference** -- Layer decomposition in NCT/NACT/NSCT workflows
- **ivy-writing-guide** -- Ivy language reference for writing layers
- **ivy-toolkit** -- MCP tool parameters for pattern analysis

**Related agents:**
- **spec-analyst** -- Specification navigation across layers

**Related workflows:**
- **build** -- Scaffolds from the 14-layer template and adds patterns interactively
