---
paths: ["**/*.ivy", "**/*.spec"]
---

## NCT — Network-Centric Compositional Testing

### Theory (Practitioner Summary)

**Compositionality**: If each component locally satisfies its specification, the composed system satisfies the global specification. This means you verify each isolate independently — you never need the full system in scope at once.

**Role inversion**: The Ivy tester plays the OPPOSITE role of what it tests. Testing a server IUT = Ivy acts as a formal client. File `{prot}_server_test_*.ivy` tests the SERVER, but IVY plays the CLIENT.

**Process-oblivious (extensional)**: Specifications describe only wire-visible behavior (packets, frames, messages). Never reference IUT internal state, threads, or implementation details.

**Test traffic generation**: Z3/SMT solver generates constrained random inputs satisfying all `before` clause guards. Each exported action is a candidate for random generation.

### Monitor Pattern

Specifications use monitors attached to protocol events:

- **`before` clauses** — Preconditions/guards. What must hold before an event. If guard fails, event is blocked.
- **`after` clauses** — State updates and compliance checks. Record history, verify received data.
- **`_finalize()`** — End-state verification. Called when the test completes. Heuristic checks (data transferred, no errors).
- **`export`** — Actions the test mirror generates randomly. `import` = actions provided by the IUT.

### NCT Workflow (10 Steps)

1. Select target protocol and RFC(s)
2. Extract testable requirements — MUST, SHOULD, MAY statements (RFC 2119)
3. Decompose protocol into the 14-layer template
4. Write type definitions (`{prot}_types.ivy`) — the foundation layer
5. Build core stack in dependency order: frames → packets → protection → connection
6. Define entity roles: client, server, optionally MIM
7. Write behavioral constraints as `before`/`after` monitors in behavior files
8. Create test specifications with `export` declarations and `_finalize`
9. Verify with `ivy_verify`, compile with `ivy_compile` (target=test)
10. Execute compiled test binary against IUT via PANTHER experiment framework

## NACT — Network-Attack Compositional Testing

Extends NCT with the APT (Advanced Persistent Threat) 6-stage lifecycle for security testing:

| Phase | Stage | File |
|---|---|---|
| Infiltration | 1. Reconnaissance | `attack_reconnaissance.ivy` |
| Infiltration | 2. Infiltration | `attack_infiltration.ivy` |
| Infiltration | 3. C2 Communication | `attack_c2_communication.ivy` |
| Expansion | 4. Privilege Escalation | `attack_privilege_escalation.ivy` |
| Expansion | 5. Persistence | `attack_maintain_persistence.ivy` |
| Extraction | 6. Exfiltration | `attack_exfiltration.ivy` |
| Cross-cutting | White Noise | `attack_white_noise.ivy` |

**Attack entities**: Attacker, Bot, C2 Server, Target, MIM. Same Ivy language, same before/after monitors, adversarial perspective. Protocol-specific bindings in `{prot}_apt_lifecycle/`. Entity definitions in `apt_entities/`, behavior in `apt_entities_behavior/`.

## NSCT — Network-Simulator Centric Compositional Testing

Same Ivy specs, different execution environment: Shadow Network Simulator instead of real Docker networks.
Provides deterministic execution (seed-controlled), scale testing (many nodes), topology control, network condition modeling (latency, loss, bandwidth). Use `type: shadow_ns` in PANTHER experiment config.

**Recommended order**: NCT first (compliance) → NACT second (security) → NSCT third (scale/conditions).

## 14-Layer Formal Model Template

| # | Layer | File Pattern | Purpose |
|---|---|---|---|
| 1 | Types | `{prot}_types.ivy` | Identifiers, bit vectors, enumerations |
| 2 | Application | `{prot}_application.ivy` | Data transfer semantics |
| 3 | Security | `{prot}_security.ivy` | Key establishment, handshake |
| 4 | Frame/Message | `{prot}_frame.ivy` | PDU definitions — protocol semantics |
| 5 | Packet | `{prot}_packet.ivy` | Wire-level structure |
| 6 | Protection | `{prot}_protection.ivy` | Encryption/decryption |
| 7 | Connection | `{prot}_connection.ivy` | Session lifecycle, state machine |
| 8 | Transport Params | `{prot}_transport_parameters.ivy` | Negotiable parameters |
| 9 | Error Handling | `{prot}_error_code.ivy` | Error taxonomy |
| 10 | Entity Defs | `ivy_{prot}_{role}.ivy` | Network participant instances |
| 11 | Entity Behavior | `ivy_{prot}_{role}_behavior.ivy` | FSM + before/after monitors |
| 12 | Shims | `{prot}_shim.ivy` | Formal model ↔ implementation bridge |
| 13 | Serialization | `{prot}_ser.ivy`, `{prot}_deser.ivy` | Wire format encoding/decoding |
| 14 | Utilities | `byte_stream.ivy`, `file.ivy`, `time.ivy`, `random_value.ivy` | Common utilities |

**Dependency order**: Types(1) → Error(9), Frame(4) → Packet(5) → Protection(6) → Connection(7) → Entities(10-12)

**Minimum viable set** (7 layers): Types, Frame, Packet, Connection, Entity Defs, Entity Behavior, Shims.

Use the `build` workflow to scaffold a new protocol model. Reference `protocol-testing/quic/` as the complete example (200+ files).
