# Phase 1: Protocol Classification

## Purpose

Determine the target protocol's shape through concrete questions, producing a protocol profile document that drives all architectural decisions in subsequent phases.

## Process

Ask classification questions ONE AT A TIME. Present each question, wait for the answer, then ask the next. Do not batch all questions into a single message.

## Classification Questions

1. **Communication pattern**: Client-server (one side initiates), peer-to-peer (either side initiates), request-response (stateless exchanges), or multicast (one-to-many)?

2. **Connection model**: Persistent connections with state, or independent message exchanges?

3. **Message structure**: Fixed-format binary, variable-format (TLV/tagged), text-based, or format that changes mid-connection (e.g., handshake vs. data phase)?

4. **Layering**: Self-contained on a transport, or layered on another protocol (e.g., DNS over QUIC)?

5. **Security model**: Own encryption/authentication, relies on underlying transport, or none?

6. **State machine complexity**: Approximate state count (2-3 simple, 5-10 moderate, 10+ complex).

7. **Testing goals**: Conformance, malformed input resilience, active attacker resistance, or all?

## Protocol Profile Output

After all questions are answered, compile a structured summary:

```
Protocol: [name] ([RFC/spec reference])
Pattern: [communication pattern], [connection model]
Transport: [underlying transport and relationship]
Messages: [format description, including mid-connection changes if any]
Security: [security model]
States: [count] ([brief description])
Testing goals: [selected goals]
Extensible: [yes/no — does the protocol support negotiated extensions?]
```

## Pattern Selection

The profile maps to which QUIC model architectural elements apply. Consult this table to determine the directory structure and file set for subsequent phases:

| Profile Trait | Architectural Effect |
|---|---|
| Stateless protocol | Skip connection state tracking, no FSM directory |
| No own crypto | Skip protection/security files and `tls_stack/`, shims pass plaintext |
| Own crypto layer | Add `tls_stack/` equivalent for the security protocol |
| P2P / symmetric | Single entity module with symmetric instantiation, shared shim |
| Multicast | Publisher entity module with multiple destination endpoints |
| Simple state machine | Inline state in stack module, no separate FSM files |
| Complex state machine | Separate `{proto}_fsm/` directory with per-role FSM files |
| Mid-connection format change | Multiple message struct types, packet type dispatch in `behavior` action |
| Attack testing desired | Add `{proto}_attacks_stack/` directory |
| Layered on another protocol | Shims interface with underlying protocol API, not raw UDP |
| Request-response | Simpler `_generating` guards, minimal inter-event state |
| Extensible protocol | Add `{proto}_extensions/` directory for negotiated capabilities |

---

**STOP.** Present the protocol profile and pattern selection to the user. Do NOT proceed to Phase 2 until the user explicitly confirms the classification is correct.
