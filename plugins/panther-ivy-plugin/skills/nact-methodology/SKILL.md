---
name: nact-methodology
description: "Use when working with NACT (Network-Attack Compositional Testing), security testing, APT lifecycle modeling, or attack entity configuration. Covers APT 6-stage lifecycle, attack entities, protocol-specific bindings."
---

## NACT -- Network-Attack Compositional Testing

### Overview

NACT extends NCT to model and test protocols from an attacker's perspective. It uses the APT (Advanced Persistent Threat) lifecycle model to systematically test security properties of protocol implementations. Attack specifications use the same Ivy formal language and before/after monitor pattern as NCT but focus on adversarial behavior.

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

### Relationship to NCT
- **NCT** verifies specification compliance (correct behavior)
- **NACT** verifies security properties (resilience to attacks)
- Both use the same Ivy formal language and before/after monitor pattern
- NACT adds attack entity roles and the APT lifecycle framework
- A comprehensive testing campaign uses both NCT and NACT

### Checkpoints — Verify Before Continuing

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Threat model defined | A threat model grounds the test in realistic attack scenarios. |
| Attack entities created | Every attack needs attacker, target, and optionally bot/C2/MIM entities in `apt_entities/`. |
| Adversarial monitors written | NACT requires adversarial monitors — NCT monitors enforce compliance, not attacks. |
| All 6 APT stages considered | All stages apply. Some may be trivial, but each must be explicitly addressed. |
| Persistence modeled | Include persistence for a complete and realistic attack model. |

### Common Mistakes

**Missing attack entity definitions**
- **Problem:** Attack spec uses generic entities instead of defining attacker-specific ones
- **Fix:** Define entities in `apt_entities/` with attack-specific state and capabilities

**Confusing NCT and NACT monitors**
- **Problem:** Using `require` (compliance check) instead of attack-specific constraints
- **Fix:** NACT monitors model what the attacker CAN do, not what the protocol SHOULD do

## Integration

**Prerequisite:** `nct-methodology` -- NACT extends NCT; understand NCT concepts first.

**Related skills:**
- **nct-methodology** -- Base NCT concepts that NACT extends
- **ivy-writing-guide** -- Ivy syntax for writing attack monitors
- **specification-patterns** -- 14-layer template (NACT reuses the same layers)
- **workflow-reference** -- Verification of attack model consistency

**Related agents:**
- **methodology-guide** -- Interactive NACT workflow execution
- **spec-analyst** -- Specification navigation and verification

**Related commands:**
- `/nct-check` -- Verify attack specifications
- `/nct-scaffold` -- Scaffold attack test specs (role=attacker)
