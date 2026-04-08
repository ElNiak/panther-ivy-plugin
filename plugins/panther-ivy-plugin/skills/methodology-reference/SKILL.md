---
name: methodology-reference
description: "Internal knowledge skill — merged NCT/NACT/NSCT methodology and workflow guidance. Do not invoke directly; loaded by build (Phase 1) and learning injection."
allowed-tools: "Read Grep Glob ToolSearch"
---

# Formal Testing Methodologies

## Methodology Selection

| Methodology | Purpose | When to Use |
|-------------|---------|-------------|
| **NCT** | Specification-based compliance testing | Testing protocol implementations against RFCs |
| **NACT** | Adversarial security testing | Testing resistance to APT-style attacks |
| **NSCT** | Simulation-based testing | Testing under controlled network conditions |

## Shared Foundations

All three methodologies share:
- **14-layer specification template** (see `specification-patterns`)
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

| Phase | Steps | Gate |
|-------|-------|------|
| **EXPLORE** | 1. Select protocol/RFC, 2. Extract requirements | Requirements manifest produced |
| **PLAN** | 3. Decompose into 14-layer template, 4-5. Design type + stack layers | Layer mapping reviewed |
| **WRITE** | 6-8. Entity roles, behavioral constraints, test specs | Each file passes `ivy_diagnostics(mode="structural")` |
| **VERIFY** | 9. `ivy_verify` + `ivy_compile` (target=test) | Zero verification errors |
| **FINALIZE** | 10. Run against IUT via PANTHER | Results collected |

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

**Missing `after init`**
- **Problem:** Relations/functions start with arbitrary values, not defaults
- **Fix:** Always include `after init` block setting initial state for all relations

**Correct role assignment**
- **Convention:** Server test files = Ivy plays client (opposite of what is tested)
- **Rule:** File name indicates WHAT IS TESTED.

**Missing bracket tags on assertions**
- **Problem:** Assertions lack `[rfcNNNN:X.Y]` comments, breaking traceability
- **Fix:** Tag every `require`/`ensure`/`assert` with its RFC section reference

**Ungrounded variables in invariants**
- **Problem:** `invariant sent(P, N)` means "for ALL P and N, sent is true"
- **Fix:** Quantify explicitly or bind variables to specific values

**Forgetting to export `_finalize`**
- **Problem:** End-state checks never execute
- **Fix:** Always include `export action _finalize` in test specifications

---

## NACT

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

**Missing attack entity definitions**
- **Problem:** Attack spec uses generic entities instead of defining attacker-specific ones
- **Fix:** Define entities in `apt_entities/` with attack-specific state and capabilities

**Confusing NCT and NACT monitors**
- **Problem:** Using `require` (compliance check) instead of attack-specific constraints
- **Fix:** NACT monitors model what the attacker CAN do, not what the protocol SHOULD do

**Skipping threat model**
- **Problem:** Writing attack specs without first identifying applicable APT stages
- **Fix:** Complete Phase 2 threat modeling before any spec work

---

## NSCT

### Core Concepts

- **Deterministic execution** — Same seed produces identical results for reproducible debugging
- **Scale testing** — Simulate many nodes without real hardware
- **Topology control** — Define arbitrary network topologies (meshes, hierarchies, partitions)
- **Network condition modeling** — Simulate latency, packet loss, bandwidth constraints, jitter
- **Spec reuse** — NSCT reuses the same Ivy specifications from NCT; the difference is the execution environment (`type: shadow_ns` vs `type: docker_compose`)

### NSCT Workflow

1. **Define network topology** — nodes, links, latencies, bandwidths, loss rates
2. **Configure simulation parameters** — duration, seed, logging level
3. **Map IUT implementations to simulated nodes** — set up protocol implementations
4. **Reuse Ivy formal specifications** — same specs from NCT (no rewrite needed)
5. **Write PANTHER experiment config** — YAML with `type: shadow_ns`
6. **Execute simulation** — `panther run --config <config.yaml>`
7. **Analyze results** — examine simulation logs and verification output
8. **Iterate** — modify topology, latency, loss rates, bandwidth and re-run

### Shadow NS Build Mode

NSCT requires a specific Z3 build mode for Shadow NS compatibility:
- Use `build_mode: ""` (empty string) in PANTHER Ivy config
- This uses the legacy `mk_make.py` build system compatible with Shadow NS
- Other build modes (`debug-asan`, `rel-lto`, `release-static-pgo`) are for NCT/NACT Docker environments

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

### Systematic Mapping Workflow

1. **Extract Requirements**: Read the RFC, list all normative statements: `Section X.Y: "text" [MUST|SHOULD|MAY] → Layer: {layer}`
2. **Classify by Layer**: Group by 14-layer template layer
3. **Identify Testable Properties**: Directly testable, indirectly testable, or not testable
4. **Write Ivy Assertions**: Determine before/after, identify the action, express as `require`
5. **Verify Consistency**: Use `ivy_verify` MCP tool

### Common Pitfalls

- **Ambiguous RFC Language**: Check errata, look at existing models, start strict
- **Untestable Requirements**: Quantitative timing, implementation-internal state, performance
- **Circular Dependencies**: Break cycles by identifying protocol flow order

---

## Verification Workflow

### Failure Patterns

| Failure Pattern | Type | Common Cause |
|---|---|---|
| `error: failed to verify invariant preservation` | Invariant not preserved | Action modifies state violating an invariant |
| `error: type mismatch` | Type safety | Incompatible types |
| `error: ungrounded variable` | Ungrounded relation | Unbound variables |
| `error: safety property violated` | Safety violation | Unsafe state reachable |
| `cannot find isolate X` | Missing isolate | Misspelled or undeclared isolate |
| `circular dependency` | Cycle | Break with abstract interface |
| `uninterpreted sort has no instances` | Missing instances | Add constructor or axiom |
| Z3 timeout / "unknown" | SMT timeout | Simplify proof, add lemmas, reduce isolate scope |

### Debugging Cycle

1. **Check**: Run `ivy_verify` MCP tool
2. **Read the error**: Note line number, error type, counterexample trace
3. **Locate**: Use `Grep` or LSP `goToDefinition` to navigate to the failing symbol
4. **Diagnose**: Missing invariant? Bug in action logic? Missing precondition?
5. **Fix**: Apply minimal fix using `Edit`. Prefer adding invariants over weakening specs.
6. **Re-check**: Run verification again. Repeat until all checks pass.

### Common Errors and Fixes

**"failed to verify" on action body**
- Check: Are all modified relations updated consistently? Does `ensure` match body?

**Using `assume` instead of `require`**
- `assume` makes the model unsound. Use `require` for preconditions.

**Ungrounded variables in invariants**
- `invariant sent(P, N)` means "for ALL P and N" — ground variables: `invariant sent(P, N) -> P = the_cid`

**Z3 timeout**
- Simplify by breaking into smaller lemmas. Add ghost state or auxiliary invariants. Use isolate boundaries.

### Verification Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Verification re-run | Run `ivy_verify` after every change — previous results prove nothing about current state. |
| Small changes verified | Small changes can break invariants. Verify even single-line edits. |
| Z3 timeout investigated | Timeout means unknown, not OK. Simplify the proof or add lemmas. |
| `require` used over `assume` | Use `require` for preconditions — `assume` weakens the model. |
| All isolate errors resolved | Isolate failures can cascade. Resolve all before continuing. |
| Verification passes before feature work | Resolve all verification failures before moving to the next requirement. |

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

### Gate Details

#### Gate 1: Structural Quality (25%)
1. Run `ivy_diagnostics(mode="structural")` — fast structural check (milliseconds)
2. Verify: `#lang ivy1.7` header, includes reference existing files, balanced braces
3. Score: 100 if 0 errors, -20 per error, -5 per warning (floor at 0)

#### Gate 2: Type Safety & Formal Properties (30%)
1. Run `ivy_verify` — formal verification
2. Parse diagnostics: success/failure, specific errors with line numbers
3. Score: 100 if verification succeeds, 0 if it fails (binary)

#### Gate 3: Semantic Correctness (20%)
1. Run `ivy_model_info` to get model structure
2. Check: naming conventions (+20), invariant coverage (+20), action require guards (+20), after init blocks (+20), no anti-patterns (+20)
3. Run `ivy_quality` (mode="suggestions") for additional hints
4. Score: sum of applicable checks (max 100)

#### Gate 4: RFC Traceability (25%)
1. Run `ivy_coverage` (mode="matrix") for requirement-to-assertion mapping
2. Run `ivy_coverage` (mode="stats") for coverage statistics
3. Check: bracket tag presence, tags match manifest, no orphaned tags, no untagged assertions
4. Score: coverage_percent + bonus for all MUST covered (cap at 100)
