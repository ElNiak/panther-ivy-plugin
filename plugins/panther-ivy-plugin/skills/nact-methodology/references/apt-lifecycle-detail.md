# APT 6-Stage Lifecycle — Full Detail

## Lifecycle Composition

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

## Phase 1: Infiltration

### Stage 1 — Reconnaissance (`attack_reconnaissance.ivy`)

Gather information about the target. Passive (OSINT, social engineering, WHOIS, DNS queries)
and active (port scanning, service enumeration, OS fingerprinting, banner grabbing).

Key actions:
- `launch_whois_lookup()` — Domain ownership discovery
- `launch_dns_query()` — DNS record enumeration
- `endpoint_scanning(src, dst)` — Active port/service scanning

### Stage 2 — Infiltration (`attack_infiltration.ivy`)

Initial access to the target network. Exploit detected vulnerabilities to establish a foothold.
This stage maps reconnaissance findings to exploitation actions.

### Stage 3 — C2 Communication (`attack_c2_communication.ivy`)

Establish command and control channels for remote control of compromised systems.
The C2 channel is the attacker's persistent communication path.

## Phase 2: Expansion

### Stage 4 — Privilege Escalation (`attack_privilege_escalation.ivy`)

Gain higher access levels within the compromised network. Exploit local vulnerabilities
or misconfigurations to move from unprivileged to privileged access.

### Stage 5 — Persistence (`attack_maintain_persistence.ivy`)

Maintain access to the compromised system across reboots and security updates.
Install backdoors, modify configurations, or establish redundant access paths.

## Phase 3: Extraction

### Stage 6 — Exfiltration (`attack_exfiltration.ivy`)

Extract data from the target network. Encode, compress, and transmit data through
covert channels or legitimate-looking traffic.

## Cross-Cutting: White Noise (`attack_white_noise.ivy`)

Distraction attacks to cover the primary attack operation. Generate benign-looking
traffic to mask exfiltration or make forensic analysis harder.

## APT Directory Structure

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

## NACT Workflow (Full 9-Step Detail)

1. **Define threat model** — identify which APT stages apply to the target protocol
2. **Design attack entities** — define roles and capabilities in `apt_entities/`
3. **Write attacker behavioral constraints** — FSM and before/after monitors in `apt_entities_behavior/`
4. **Create protocol-specific bindings** — map generic attack stages to protocol actions in `{prot}_apt_lifecycle/`
5. **Write attack test specifications** — tests in `apt_tests/`
6. **Verify attack specs** — use `ivy_verify` MCP tool for model consistency
7. **Compile attack tests** — use `ivy_compile` MCP tool for executables
8. **Execute against IUT** — run via PANTHER
9. **Analyze security properties** — verify confidentiality, integrity, availability
