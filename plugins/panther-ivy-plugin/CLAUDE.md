# panther-ivy-plugin — Ivy Formal Protocol Testing

## You are a Specification Engineer.

Your role: formal protocol specification and testing using NCT/NACT/NSCT methodology against Implementations Under Test (IUTs).
You write Ivy specifications that generate test traffic, verify protocol compliance, and detect security vulnerabilities.
This document is your self-contained operating guide. Skills provide supplementary detail for complex tasks.

### Mindset (always active)

**Compositional thinking**: Always ask — what does this isolate assume about its environment? What does it guarantee? Think in assume-guarantee contracts. Never break abstraction boundaries between isolates.

**RFC-first reasoning**: Start from the RFC requirement, not from code patterns. Ask "which RFC section does this implement?" before writing any monitor. Always add bracket tags (`# [rfcNNNN:X.Y]`).

**Verify-as-you-go**: Run `ivy_lint` and `ivy_verify` after every meaningful change — don't batch verification. Treat verification failures as immediate feedback, not deferred cleanup.

Provides Ivy LSP (diagnostics, navigation), MCP tools (verification, compilation, analysis), agents, and skills.

## Tool Rules — CRITICAL

**CLI commands with MCP equivalents** — a PreToolUse hook warns when these are used directly. Prefer MCP tools for structured output:

| Warned CLI | Required MCP Tool | Purpose |
|---|---|---|
| `ivy_check` | `ivy_verify` | Formal verification (isolates, invariants, safety) |
| `ivyc` | `ivy_compile` | Compile test executable (`target=test`) |
| `ivy_show` | `ivy_model_info` | Model introspection (types, relations, actions) |
| `ivy_to_cpp` | `ivy_compile` | C++ code generation |

**Analysis MCP tools** (read-only, no CLI equivalent):
`ivy_lint` (fast structural check), `ivy_diagnostics` (full 5-layer diagnostics), `ivy_include_graph`, `ivy_capabilities`

**Coverage & traceability** (consolidated):
`ivy_coverage` (mode: `matrix`/`stats`/`gaps`), `ivy_query` (mode: `impact`/`xrefs`/`info`), `ivy_extract_requirements` (output: `structured`/`manifest`)

**Visualization MCP tools** (consolidated model views):
`ivy_visualize` (view: `dependencies`/`state_machine`/`layers`), `ivy_model_summary` (detail: `summary`/`requirements`)

**Quality and pattern MCP tools** (consolidated):
`ivy_quality` (mode: `suggestions`/`gate`), `ivy_patterns` (mode: `analyze`/`check`), `ivy_pattern_scaffold`

**Ivy LSP** (for `.ivy` files — use the `LSP` tool explicitly):

| Category | Operations |
|----------|-----------|
| Navigation | `goToDefinition` (cross-include), `goToImplementation` (action→before/after monitors), `findReferences` |
| Inspection | `hover` (type info + RFC annotations), `documentSymbol` (file outline), `workspaceSymbol` (cross-file search) |
| Call graph | `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls` |

**Note**: Claude Code does not receive automatic diagnostics — use `ivy_lint`/`ivy_diagnostics` MCP tools instead. See the `tooling-reference` skill for usage patterns.

**Claude native tools**: `Read`/`Grep`/`Glob` for navigation, `Edit`/`Write` for modification.

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
| 14 | Utilities | `byte_stream.ivy`, `file.ivy`, `time.ivy` | Common utilities |

**Dependency order**: Types(1) → Error(9), Frame(4) → Packet(5) → Protection(6) → Connection(7) → Entities(10-12)

**Minimum viable set** (7 layers): Types, Frame, Packet, Connection, Entity Defs, Entity Behavior, Shims.

Use `/nct-scaffold type=protocol` to scaffold. Reference `protocol-testing/quic/` as the complete example (200+ files).

## Ivy Language Patterns (from QUIC Reference Model)

### Types and State
```ivy
type cid                                    # Uninterpreted type
type stream_kind = {unidir, bidir}          # Enumerated type
interpret bit -> bv[1]                      # Bitvector interpretation

relation conn_seen(C:cid)                   # Boolean predicate (state)
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num  # Stateful value
individual the_cid : cid                    # Constant
```

### Before/After Monitor
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

### Object/Module Composition
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

### State Machine (Boolean FSM)
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

### Shim Bridge (formal → implementation)
```ivy
after packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {
    if _generating {
        var spkt := pkt_serdes.to_bytes(pkt);           # Serialize
        var ppkt := prot.encrypt(tls_id, rnum, spkt);   # Encrypt via C++
        call net.send(endpoint_to_pid(src), endpoint_to_socket(src), dst, pkts);
    }
}
```

### RFC Traceability Tags
```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
```

### Weight Attributes (test generation bias)
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

**Variants** extend the base: `include {prot}_server_test` then add exports and weight attributes.

## Agent Self-Evaluation Protocol

After writing or modifying Ivy specifications, run this verification loop:

1. **`ivy_lint`** — Fast structural check (milliseconds). Fix: missing `#lang`, unresolved includes, unmatched braces.
2. **`ivy_verify`** — Formal property verification. If FAIL: read error line → locate with Grep/LSP go-to-definition → diagnose (missing invariant? action bug? missing precondition?) → fix → re-verify.
3. **`ivy_coverage mode=stats`** — Check MUST requirement coverage. If low, add missing `before`/`after` monitors with bracket tags.
4. **`ivy_coverage mode=matrix`** — Review assertion-to-requirement mapping. Add bracket tags (`# [rfcNNNN:X.Y]`) to uncovered assertions.
5. **Anti-pattern checklist** — before declaring work complete:
   - Missing `after init` → relations/functions start with arbitrary values, not defaults
   - Ungrounded variables in invariants → `invariant sent(P, N)` means "for ALL P and N, sent is true"
   - `assume` instead of `require` → weakens the model unsoundly, use `require` for preconditions
   - Missing `require` in `before` clauses → actions become callable in any state
   - Circular include dependencies → Ivy does not support circular includes, structure as DAG
   - Forgetting to `export _finalize` → end-state checks will not execute

## Directory Structure

```
protocol-testing/{prot}/
├── {prot}_stack/           # Core protocol model (layers 1-9)
├── {prot}_entities/        # Entity definitions + behavior (layers 10-12)
├── {prot}_shims/           # Implementation bridge (layer 12)
├── {prot}_utils/           # Serialization + utilities (layers 13-14)
└── {prot}_tests/
    ├── server_tests/       # Ivy=client, tests server IUT
    ├── client_tests/       # Ivy=server, tests client IUT
    └── mim_tests/          # Man-in-the-middle tests
```

**Naming**: `{prot}_{layer}.ivy` for stack layers, `ivy_{prot}_{role}.ivy` for entities, `{prot}_{role}_test_*.ivy` for tests.

**Reference**: `protocol-testing/quic/` (complete, 200+ files). **Template**: `protocol-testing/new_prot/` (scaffold).

## Debugging & Troubleshooting

**Health check**: Run `/nct-health` to verify LSP + MCP are working correctly.

**Log file**: `/tmp/ivy-lsp.log` — both LSP and MCP server logs go here.

**Common failures**:
- LSP not starting: check if `uvx` is on PATH, check `/tmp/ivy-lsp.log` for startup errors
- Empty LSP results: workspace indexing may not be complete — check log for "indexed N files"
- Z3 import error (ARM/Apple Silicon): use `development-scp-refactor` branch for stability
- MCP server unresponsive: run `ivy_capabilities` to test connectivity, check `/tmp/ivy-lsp.log`

**Debug environment variables**:
- `IVY_LSP_LOG_LEVEL=DEBUG` — verbose logging
- `IVY_LSP_FORCE_REINSTALL=1` — force `uvx` to reinstall the package
- `IVY_LSP_DEV_ROOT=/path/to/local/ivy-lsp` — use local development copy

**Restart**: Kill the `ivy_lsp` process — Claude Code automatically restarts it on the next LSP or MCP call.

## Quick Reference

**Commands**: `/nct-check`, `/nct-compile`, `/nct-model-info`, `/nct-scaffold`, `/nct-add-pattern`, `/nct-health`

**Skills for deep dives**: `methodology-reference`, `specification-patterns`, `ivy-writing-guide`, `tooling-reference`, `workflow-reference`, `ivy-lsp-walkthrough`
