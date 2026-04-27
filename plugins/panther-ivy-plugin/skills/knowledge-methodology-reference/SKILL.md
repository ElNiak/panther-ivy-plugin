---
name: knowledge-methodology-reference
description: "Use when choosing a testing methodology, starting model construction, or mapping RFC requirements to an Ivy testing strategy. Provides NCT (compliance) / NACT (security) / NSCT (simulation) selection and workflow guidance."
user-invocable: false
---

# Formal Testing Methodologies

**Type:** flexible — adapt principles to context.

## Methodology Selection

| Methodology | Purpose | When to Use |
|-------------|---------|-------------|
| **NCT** | Specification-based compliance testing | Testing protocol implementations against RFCs |
| **NACT** | Adversarial security testing | Testing resistance to APT-style attacks |
| **NSCT** | Simulation-based testing | Testing under controlled network conditions |

## Shared Foundations

All three methodologies share:
- **14-layer specification template** — canonical table location is documented in `.claude/rules/nct-methodology.md`; optional-layer discussion and scaffolding decisions live in `specification-patterns`.
- **Before/after monitor pattern** for behavioral assertions
- **`require`/`export`/`_finalize` semantics** for invariant enforcement
- **Role inversion** (Ivy tester acts as the opposite role of the IUT)

## Quick Decision Tree

1. **Testing RFC compliance?** → NCT
2. **Testing security against attacks?** → NACT
3. **Testing under network conditions?** → NSCT
4. **Not sure?** → Start with NCT (the foundation for both NACT and NSCT)

For tool usage across all methodologies, see `ivy-toolkit`.

---

## NCT

### Core Concepts

#### Role Inversion
The Ivy tester's role is the **opposite** of what it tests:
- Testing a server IUT → Ivy acts as a formal client (`{prot}_server_test_*.ivy` files)
- Testing a client IUT → Ivy acts as a formal server (`{prot}_client_test_*.ivy` files)
- MIM testing → Ivy acts as man-in-the-middle (`{prot}_mim_test_*.ivy` files)

**Rule:** File name indicates WHAT IS TESTED. `quic_server_test_*.ivy` = testing the server, Ivy plays client.

#### Specification Structure
Protocol specs use **monitors** (before/after clauses) attached to protocol events:

- **before clauses** — Preconditions/guards. Define what must hold before an event occurs. If the precondition fails, the event is blocked.
- **after clauses** — State updates/checks. Record history by updating shared variables. Check specification compliance of received data.
- **_finalize()** — End-state verification. Called when the test completes. Performs heuristic checks (e.g., data was received, no errors occurred).

#### Test Traffic Generation
Specifications use `export` to declare actions that the test mirror generates randomly. Z3/SMT solving ensures generated traffic complies with specification constraints. `import` actions are provided by the IUT.

### NCT Workflow Summary

Load `references/comprehensive-methodology-detail.md` for the full 10-step NCT workflow with tool guidance.

### Directory Structure

```
protocol-testing/{prot}/
|-- {prot}_stack/          # Core protocol model (layers 1-9)
|-- {prot}_entities/       # Entity definitions and behavior
|-- {prot}_shims/          # Implementation bridge
|-- {prot}_utils/          # Serialization, utilities
+-- {prot}_tests/
    |-- server_tests/      # Tests targeting server IUTs
    |-- client_tests/      # Tests targeting client IUTs
    +-- mim_tests/         # Man-in-the-middle tests
```

**Naming**: `{prot}_{layer}.ivy` for stack layers, `ivy_{prot}_{role}.ivy` for entities, `{prot}_{role}_test_*.ivy` for tests.

### NCT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Type layer complete | Types are the foundation — all other layers depend on them being defined first. |
| Verification passes | Verify after every meaningful change — errors compound when deferred. |
| RFC consulted | RFC is the source of truth for every requirement and assertion. |
| Bracket tags present | Every assertion has a `# [rfcNNNN:X.Y]` tag for traceability. |
| Role inversion correct | Testing a server = Ivy acts as client. File names reflect what is tested. |
| `_finalize` exported | End-state properties require `_finalize` to execute. |

### Common NCT Mistakes

See the `ivy-error-patterns` skill for the full error-to-fix lookup table. The most frequent NCT-specific mistakes:
- Missing `after init` (error pattern #12) — relations start with arbitrary values
- Ungrounded variables (error pattern #2) — `invariant sent(P,N)` means "for ALL P,N"
- Missing bracket tags — tag every assertion with `# [rfcNNNN:X.Y]`
- Missing `export _finalize` — end-state checks never execute
- Wrong role assignment — file name indicates WHAT IS TESTED (server test = Ivy plays client)

---

## NACT

For the concrete pattern library backing NACT (stage-file scaffolding, attack-entity composition, protocol-binding template, `around`-block monitors), load the `apt-attack-patterns` skill via the `Skill` tool.

### APT 6-Stage Lifecycle

The attack lifecycle is organized into 3 phases with 6 stages plus a cross-cutting concern:

| Phase | Stage | File |
|---|---|---|
| Infiltration | 1. Reconnaissance | `attack_reconnaissance.ivy` |
| Infiltration | 2. Infiltration | `attack_infiltration.ivy` |
| Infiltration | 3. C2 Communication | `attack_c2_communication.ivy` |
| Expansion | 4. Privilege Escalation | `attack_privilege_escalation.ivy` |
| Expansion | 5. Persistence | `attack_maintain_persistence.ivy` |
| Extraction | 6. Exfiltration | `attack_exfiltration.ivy` |
| Cross-cutting | White Noise | `attack_white_noise.ivy` |

### Attack Entities

NACT defines additional entity roles beyond NCT's client/server: **Attacker**, **Bot**, **C2 Server**, **Target**, **MIM** (Man-in-the-Middle).

Entity definitions reside in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`. Protocol-specific bindings map generic attack stages to concrete protocol actions in `{prot}_apt_lifecycle/`.

### NACT vs NCT Monitors

| Aspect | NCT Monitor | NACT Monitor |
|--------|-------------|--------------|
| Perspective | Protocol compliance | Adversarial capability |
| `require` semantics | "Protocol MUST do this" | "Attacker CAN do this if..." |
| State tracking | Connection/stream state | Attack progress, footholds |
| `_finalize` checks | Data transferred, no errors | Attack objectives achieved |

### NACT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Threat model defined | A threat model grounds the test in realistic attack scenarios. |
| Attack entities created | Every attack needs attacker, target, and optionally bot/C2/MIM entities in `apt_entities/`. |
| Adversarial monitors written | NACT requires adversarial monitors — NCT monitors enforce compliance, not attacks. |
| All 6 APT stages considered | All stages apply. Some may be trivial, but each must be explicitly addressed. |
| Persistence modeled | Include persistence for a complete and realistic attack model. |

### Common NACT Mistakes

- Missing attack entity definitions — define entities in `apt_entities/` with attack-specific state
- Confusing NCT and NACT monitors — NACT models what the attacker CAN do, not compliance
- Skipping threat model — complete threat modeling before spec work

---

## NSCT

Simulation-based testing via Shadow Network Simulator. Reuses NCT Ivy specs; difference is `type: shadow_ns` in PANTHER config. Requires `build_mode: ""` (Shadow-compatible). Load `references/comprehensive-methodology-detail.md` for topology config examples and NCT vs NSCT comparison.

### NSCT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Topology design complete | Phase 2 must produce a validated node/link topology before any config writing. |
| Simulation config defined | Proper topology ensures the simulation tests what you intend. |
| Correct build mode selected | Shadow requires `build_mode: ""` — other modes are for NCT/NACT Docker environments. |
| Deterministic seed configured | Reproducibility is Shadow's key advantage. Always set and document seeds. |
| Network conditions modeled | Latency/loss/bandwidth modeling is the reason to use Shadow over Docker. |
| Configuration validated | Run `panther config validate --config <file>` before execution. |

### Common NSCT Mistakes

**Wrong build mode**
- **Rule:** Use empty string `""` build mode for Shadow NS compatibility; other modes are for NCT/NACT Docker environments

**Missing seed configuration**
- **Problem:** Tests run with random seeds, losing reproducibility
- **Fix:** Always configure `seed` in the experiment YAML for Shadow runs

**Skipping topology design**
- **Problem:** Jumping directly to YAML config without planning node layout and link characteristics
- **Fix:** Complete Phase 2 topology design before writing config

**Using NCT Docker environment by accident**
- **Problem:** Config uses `type: docker_compose` instead of `type: shadow_ns`
- **Fix:** Verify the `network_environment.type` field is set to `shadow_ns`

---

## RFC-to-Ivy Mapping

### RFC Normative Language

RFC 2119 defines key requirement levels:

| Keyword | Meaning | Testability |
|---|---|---|
| **MUST** / **MUST NOT** | Absolute requirement/prohibition | Directly testable — map to `require` assertions |
| **SHOULD** / **SHOULD NOT** | Recommended/not recommended | Testable with weaker assertions or warnings |
| **MAY** | Optional behavior | Not directly testable — test that handling is correct when present |

### Mapping Patterns

#### MUST → require in before/after
RFC: "A server MUST NOT send data in excess of either limit."
```ivy
after frame.stream.handle(f) {
    require f.offset + f.length <= max_stream_data(f.stream_id);  # [rfc9000:4.1]
    require total_data_sent <= max_data;                           # [rfc9000:4.1]
}
```

#### MUST NOT → require negation
RFC: "An endpoint MUST NOT send a MAX_STREAMS frame with a value greater than 2^60."
```ivy
before frame.max_streams.handle(f) {
    require f.max_streams <= 0x1000000000000000;  # [rfc9000:4.6]
}
```

#### Connection MUST be closed → error handling
RFC: "If a max_streams transport parameter is received with a value greater than 2^60, the connection MUST be closed immediately with TRANSPORT_PARAMETER_ERROR."
```ivy
after transport_parameter_event(src, dst, tp) {
    if tp.max_streams > 0x1000000000000000 {
        require connection_error(the_cid) = transport_parameter_error;  # [rfc9000:4.6]
    }
}
```

#### State transitions → before guards
RFC: "A client MUST NOT send a Handshake packet before receiving the server's Initial packet."
```ivy
before packet_event(src, dst, pkt) {
    if pkt.hdr.ptype = handshake & is_client(src) {
        require server_initial_received(the_cid);  # [rfc9000:17.2.2]
    }
}
```

#### Counting/ordering → after state updates
RFC: "ACK frames MUST acknowledge the most recently received packet."
```ivy
after frame.ack.handle(f) {
    require f.largest_acknowledged >= last_received_pkt_num(the_cid);  # [rfc9000:13.2]
    conn_ack_count(the_cid) := conn_ack_count(the_cid) + 1;
}
```

### Ivy Constructs Reference

| Ivy Construct | Use For | Example |
|---|---|---|
| `require` | Assertions that must hold (MUST/MUST NOT) | `require pkt.version = negotiated_version;` |
| `before action(...)` | Preconditions before an event | Guards, state checks |
| `after action(...)` | Postconditions/updates after an event | State updates, compliance checks |
| `invariant` | Properties that always hold | `invariant conn_state(C) ~= closed -> has_cid(C)` |
| `relation` | Boolean state variables | `relation connected(cid)` |
| `function` | State variables with return type | `function conn_state(cid) : connection_state` |
| `action` | Protocol events | `action packet_event(src:endpoint, dst:endpoint, pkt:packet)` |
| `export` | Actions generated by test mirror | `export frame.stream.handle` |
| `import` | Actions provided by implementation | `import action send_packet` |

### Common Pitfalls

- **Ambiguous RFC Language**: Check errata, look at existing models, start strict
- **Untestable Requirements**: Quantitative timing, implementation-internal state, performance
- **Circular Dependencies**: Break cycles by identifying protocol flow order

---

## Verification Workflow

Load `references/comprehensive-methodology-detail.md` for failure patterns, debugging cycle, common errors, and verification checkpoints.

---

## Quality Gates

### Quality Dimensions

| Dimension | Weight | Tool Used | What It Checks |
|-----------|--------|-----------|----------------|
| Structural | 25% | `ivy_diagnostics(mode="structural")` | `#lang` header, balanced braces, includes, file structure |
| Type Safety | 30% | `ivy_verify` | Formal verification, invariants, type correctness |
| Semantic | 20% | `ivy_model_info` + checklist | Naming, invariant coverage, guards, initialization |
| Traceability | 25% | `ivy_coverage` (mode="matrix") | Bracket tags, RFC coverage, orphaned/untagged assertions |

### Scoring

- Each dimension scores 0-100
- **Overall** = structural(25%) + type_safety(30%) + semantic(20%) + traceability(25%)
- **PASS**: overall >= 70 AND no dimension at 0
- **FAIL**: overall < 70 OR any dimension at 0

### Gate Tools

| Gate | Tool | Pass Condition |
|------|------|----------------|
| Structural (25%) | `ivy_diagnostics(mode="structural")` | 0 errors; -20/error, -5/warning |
| Type Safety (30%) | `ivy_verify` | Verification succeeds (binary) |
| Semantic (20%) | `ivy_model_info` + `ivy_quality(mode="suggestions")` | Naming, guards, init blocks, no anti-patterns |
| Traceability (25%) | `ivy_coverage(mode="matrix")` + `ivy_coverage(mode="stats")` | All MUST assertions tagged `[rfcNNNN:X.Y]` |
