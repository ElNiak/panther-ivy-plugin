# Comprehensive Methodology Detail

Extracted reference material for NCT, NACT, and NSCT methodologies.
For overview and decision guidance, see the parent `SKILL.md`.

---

## NCT -- Network-Centric Compositional Testing (Full Detail)

### NCT 10-Step Workflow

#### Step 1: Select Target Protocol and RFC
Identify the protocol to test and the RFC(s) defining it. Extract testable requirements (MUST, SHOULD, MAY statements).

#### Step 2: Decompose into 14 Formal Layers
Map RFC sections to the 14-layer template. Minimum viable set:
1. Types -> Frames -> Packets -> Connection (core data flow)
2. Entity definitions -> Entity behavior -> Shims (participants)
3. Test specifications (verification)

#### Step 3: Write Type Definitions
Start with `{prot}_types.ivy` -- the foundation layer defining identifiers, bit vectors, enumerations used throughout the model.

#### Step 4: Build Core Protocol Stack
Progress through layers in dependency order:
- Frame/Message layer (`{prot}_frame.ivy`) -- PDU definitions
- Packet layer (`{prot}_packet.ivy`) -- wire-level structure
- Protection layer (`{prot}_protection.ivy`) -- encryption/decryption
- Connection layer (`{prot}_connection.ivy`) -- session lifecycle

#### Step 5: Define Entity Roles
Create entity definitions for each protocol participant:
- `ivy_{prot}_client.ivy` -- client instance
- `ivy_{prot}_server.ivy` -- server instance
- Optionally: MIM, attacker roles

#### Step 6: Write Behavioral Constraints
Encode RFC requirements as before/after monitors in `ivy_{prot}_{role}_behavior.ivy`. This is the largest and most complex protocol-specific code.

#### Step 7: Create Test Specifications
Write role-specific test files:
```ivy
#lang ivy1.7
include order
include {prot}_infer
include file
include ivy_{prot}_shim_client
include ivy_{prot}_client_behavior

after init {
    # Initialize sockets, TLS, transport parameters
}

# Export actions for test mirror generation
export frame.ack.handle
export frame.stream.handle
export packet_event

# End-state verification
export action _finalize = {
    require is_no_error;
    require conn_total_data(the_cid) > 0;
}
```

#### Step 8: Verify with ivy-tools
Use `ivy_verify` MCP tool to verify formal properties: isolate assumptions, invariants, safety properties.

#### Step 9: Compile Test
Use `ivy_compile` MCP tool with `target=test` to produce executable test binary.

#### Step 10: Execute Against IUT
Run compiled test against the implementation via PANTHER experiment framework.

### NCT Tools

| Step | Tool | Usage |
|---|---|---|
| Formal verification | `ivy_verify` | Check isolate/invariant/safety properties |
| Compile tests | `ivy_compile` | Build test executables (target=test) |
| Inspect model | `ivy_model_info` | View types, relations, actions, invariants |
| Fast structural lint | `ivy_lint` | Quick structural checks |

### NCT Directory Structure

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

### QUIC Reference Example

The QUIC model (`protocol-testing/quic/`) is the most complete NCT implementation with 50+ test variants covering: stream handling, connection close, retry, migration, transport parameter validation, error conditions, 0-RTT, congestion control, loss recovery, version negotiation, timeout handling.

Examine `quic_server_test.ivy` as the canonical test structure example.

### NCT Red Flags -- STOP

| Rationalization | Reality |
|----------------|---------|
| "I can skip the type layer" | Types are the foundation. Everything depends on them. |
| "Verification can wait until the end" | Verify after every meaningful change. Errors compound. |
| "I know this protocol well enough to skip the RFC" | RFC is the source of truth. Your memory is not. |
| "This monitor doesn't need a bracket tag" | Every assertion needs traceability. No exceptions. |
| "Role inversion doesn't matter for this test" | It always matters. Testing a server = Ivy acts as client. |
| "I'll add _finalize later" | Without _finalize, end-state properties are never checked. |
| "Direct ivy_check is faster" | MCP tools are required. The hook will block you anyway. |

### NCT Common Mistakes

**Missing `after init`**
- **Problem:** Relations/functions start with arbitrary values, not defaults
- **Fix:** Always include `after init` block setting initial state for all relations

**Wrong role in test file name**
- **Problem:** File named `quic_client_test_*.ivy` but Ivy plays client role, creating confusion
- **Fix:** File name indicates WHAT IS TESTED, not what Ivy plays. `quic_server_test_*.ivy` = testing the server.

**Missing bracket tags on assertions**
- **Problem:** Assertions lack `[rfcNNNN:X.Y]` comments, breaking traceability
- **Fix:** Tag every `require`/`ensure`/`assert` with its RFC section reference

---

## NACT -- Network-Attack Compositional Testing (Full Detail)

### APT 6-Stage Lifecycle

The attack lifecycle is organized into 3 phases with 6 stages plus a cross-cutting concern:

**Phase 1: Infiltration**
1. **Reconnaissance** (`attack_reconnaissance.ivy`) -- Gather information about the target. Passive (OSINT, social engineering, WHOIS, DNS queries) and active (port scanning, service enumeration, OS fingerprinting, banner grabbing).
   - Key actions: `launch_whois_lookup()`, `launch_dns_query()`, `endpoint_scanning(src, dst)`

2. **Infiltration** (`attack_infiltration.ivy`) -- Initial access to the target network. Exploit detected vulnerabilities to establish a foothold.

3. **C2 Communication** (`attack_c2_communication.ivy`) -- Establish command & control channels for remote control of compromised systems.

**Phase 2: Expansion**
4. **Privilege Escalation** (`attack_privilege_escalation.ivy`) -- Gain higher access levels within the compromised network.

5. **Persistence** (`attack_maintain_persistence.ivy`) -- Maintain access to the compromised system across reboots and security updates.

**Phase 3: Extraction**
6. **Exfiltration** (`attack_exfiltration.ivy`) -- Extract data from the target network.

**Cross-cutting: White Noise** (`attack_white_noise.ivy`) -- Distraction attacks to cover the primary attack operation.

### Lifecycle Composition

The master file `attack_life_cycle.ivy` composes all stages:
```ivy
#lang ivy1.7
include attack_white_noise
# Infiltration
include attack_reconnaissance
include attack_infiltration
include attack_c2_communication
# Expansion
include attack_privilege_escalation
include attack_maintain_persistence
# Extraction
include attack_exfiltration
```

### Attack Entities

NACT defines additional entity roles beyond NCT's client/server:
- **Attacker** -- Active adversary initiating attacks
- **Bot** -- Compromised system under attacker control
- **C2 Server** -- Command & control infrastructure
- **Target** -- System being attacked
- **MIM (Man-in-the-Middle)** -- Intermediary intercepting communications

Entity definitions reside in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`.

### Protocol-Specific Bindings

| Protocol | Binding Directory | Description |
|---|---|---|
| QUIC | `quic_apt_lifecycle/` | Maps attacks to QUIC connection manipulation |
| MiniP | `minip_apt_lifecycle/` | Simplified protocol attack bindings |
| UDP | `udp_apt_lifecycle/` | Basic datagram-level attacks |
| Stream Data | `stream_data_apt_lifecycle/` | Stream-oriented attack bindings |

### NACT Workflow

1. Define threat model -- identify which APT stages apply to the target protocol
2. Design attack entities -- define roles and capabilities in `apt_entities/`
3. Write attacker behavioral constraints -- FSM and before/after monitors in `apt_entities_behavior/`
4. Create protocol-specific bindings -- map generic attack stages to protocol actions in `{prot}_apt_lifecycle/`
5. Write attack test specifications -- tests in `apt_tests/`
6. Verify attack specs -- use `ivy_verify` MCP tool for model consistency
7. Compile attack tests -- use `ivy_compile` MCP tool for executables
8. Execute against IUT -- run via PANTHER
9. Analyze security properties -- verify confidentiality, integrity, availability

### APT Directory Structure

```
protocol-testing/apt/
|-- apt_entities/              # Attack entity definitions
|-- apt_entities_behavior/     # Attack entity behavioral constraints
|-- apt_lifecycle/             # 6-stage lifecycle definitions
|   |-- attack_life_cycle.ivy  # Master include file
|   |-- attack_reconnaissance.ivy
|   |-- attack_infiltration.ivy
|   |-- attack_c2_communication.ivy
|   |-- attack_privilege_escalation.ivy
|   |-- attack_maintain_persistence.ivy
|   |-- attack_exfiltration.ivy
|   |-- attack_white_noise.ivy
|   |-- quic_apt_lifecycle/    # QUIC-specific bindings
|   |-- minip_apt_lifecycle/   # MiniP-specific bindings
|   +-- udp_apt_lifecycle/     # UDP-specific bindings
|-- apt_network/               # Attack network infrastructure
|-- apt_protocols/             # Protocol-specific APT integration
|-- apt_shims/                 # Attack implementation bridges
|-- apt_stack/                 # Attack protocol stack layers
|-- apt_tests/                 # Attack test specifications
+-- apt_utils/                 # Attack utilities
```

### NACT vs NCT

- **NCT** verifies specification compliance (correct behavior)
- **NACT** verifies security properties (resilience to attacks)
- Both use the same Ivy formal language and before/after monitor pattern
- NACT adds attack entity roles and the APT lifecycle framework
- A comprehensive testing campaign uses both NCT and NACT

### NACT Red Flags -- STOP

| Rationalization | Reality |
|----------------|---------|
| "I can skip the threat model definition" | Without a threat model, you're testing random behavior, not attacks. |
| "This attack doesn't need entity definitions" | Every attack needs attacker, target, and optionally bot/C2/MIM entities. |
| "I can reuse the NCT behavior files directly" | NACT requires adversarial monitors -- NCT monitors enforce compliance, not attacks. |
| "The APT stages don't apply to this protocol" | All 6 stages apply. Some may be trivial, but they must be considered. |
| "I'll add persistence modeling later" | Without persistence, the attack model is incomplete and unrealistic. |

### NACT Common Mistakes

**Missing attack entity definitions**
- **Problem:** Attack spec uses generic entities instead of defining attacker-specific ones
- **Fix:** Define entities in `apt_entities/` with attack-specific state and capabilities

**Confusing NCT and NACT monitors**
- **Problem:** Using `require` (compliance check) instead of attack-specific constraints
- **Fix:** NACT monitors model what the attacker CAN do, not what the protocol SHOULD do

---

## NSCT -- Network-Simulator Centric Compositional Testing (Full Detail)

### Shadow Network Simulator Integration
Shadow NS provides deterministic network simulation within PANTHER:
- **Deterministic execution** -- Same seed produces identical results, enabling reproducible debugging
- **Scale testing** -- Simulate many nodes simultaneously without real hardware
- **Topology control** -- Define arbitrary network topologies (meshes, hierarchies, partitions)
- **Network condition modeling** -- Simulate latency, packet loss, bandwidth constraints, jitter

### PANTHER Environment Configuration

NSCT uses PANTHER's experiment configuration with `type: shadow_ns` network environment:

```yaml
tests:
  - name: "NSCT Protocol Test"
    network_environment:
      type: shadow_ns
      topology:
        nodes:
          - name: client_node
            ip: "10.0.0.1"
          - name: server_node
            ip: "10.0.0.2"
        links:
          - source: client_node
            target: server_node
            latency: "50ms"
            bandwidth: "10Mbit"
            loss: "0.1%"
      simulation:
        duration: "60s"
        seed: 42
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
```

### When to Use NSCT vs NCT

| Criterion | NCT (Real Network) | NSCT (Simulated) |
|---|---|---|
| Fidelity | High (real OS stack) | Medium (simulated stack) |
| Scale | Limited (container resources) | High (many simulated nodes) |
| Determinism | Non-deterministic | Deterministic |
| Topology control | Basic (Docker networks) | Full (arbitrary topologies) |
| Network conditions | Limited manipulation | Full control (latency, loss, bandwidth) |
| Debugging | Harder (non-deterministic) | Easier (deterministic replay) |
| Performance testing | Realistic | Simulated |

**Choose NSCT when:** testing under specific network conditions, testing at scale, needing deterministic reproducibility, exploring complex topologies, running regression tests.

**Choose NCT when:** needing realistic network stack behavior, testing actual performance, verifying against real-world conditions, final validation before deployment.

### NSCT Workflow

1. Define network topology -- nodes, links, latencies, bandwidths, loss rates
2. Configure simulation parameters -- duration, seed, logging level
3. Set up protocol implementations -- map IUT implementations to simulated nodes
4. Define formal specifications -- reuse the same Ivy specifications from NCT
5. Write PANTHER experiment config -- YAML with `type: shadow_ns`
6. Execute simulation -- `panther run --config <config.yaml>`
7. Analyze results -- examine simulation logs and verification output
8. Iterate with different conditions -- modify topology, latency, loss rates, bandwidth

### Shadow NS Build Mode

NSCT requires a specific Z3 build mode for Shadow NS compatibility:
- Use `build_mode: ""` (empty string) in the PANTHER Ivy config
- This uses the legacy `mk_make.py` build system compatible with Shadow NS
- Other build modes (`debug-asan`, `rel-lto`, `release-static-pgo`) are for NCT/NACT Docker environments

### NSCT Red Flags -- STOP

| Rationalization | Reality |
|----------------|---------|
| "I can skip the simulation config" | Without proper topology, your simulation doesn't test what you think it tests. |
| "The same Docker build works for Shadow" | Shadow requires specific build modes. Use the right `build_mode` setting. |
| "Deterministic seeds don't matter for this test" | Determinism is Shadow's key advantage. Always set and document seeds. |
| "I don't need network condition modeling" | If you're not using latency/loss/bandwidth, why use Shadow at all? |

### NSCT Common Mistakes

**Wrong build mode**
- **Problem:** Using Docker build mode instead of Shadow-compatible mode
- **Fix:** Use empty string `""` build mode for Shadow NS compatibility

**Missing seed configuration**
- **Problem:** Tests run with random seeds, losing reproducibility
- **Fix:** Always configure `seed` in the experiment YAML for Shadow runs

---

## Comprehensive Testing Strategy

A complete protocol verification campaign combines all three methodologies:

1. **NCT first** -- Verify basic specification compliance with real network
2. **NACT second** -- Test resilience against attack scenarios
3. **NSCT third** -- Verify behavior at scale and under adverse conditions

Each methodology shares the same Ivy formal specifications but applies them in different execution contexts, providing comprehensive coverage of protocol correctness, security, and robustness.
