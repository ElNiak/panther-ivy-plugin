---
name: NACT Methodology
description: This skill should be used when the user asks about "attack testing", "APT", "threat modeling", "security verification", "NACT", "attack lifecycle", "attacker specification", "security testing with Ivy", "penetration testing formal model", or mentions designing attack entities or writing attacker test specifications in the PANTHER Ivy framework.
---

# NACT — Network-Attack Compositional Testing

## Overview

NACT extends NCT to model and test protocols from an attacker's perspective. It uses the APT (Advanced Persistent Threat) lifecycle model to systematically test security properties of protocol implementations. Attack specifications use the same Ivy formal language and before/after monitor pattern as NCT but focus on adversarial behavior.

## Core Concepts

### APT 6-Stage Lifecycle

The attack lifecycle is organized into 3 phases with 6 stages plus a cross-cutting concern:

**Phase 1: Infiltration**
1. **Reconnaissance** (`attack_reconnaissance.ivy`) — Gather information about the target. Passive (OSINT, social engineering, WHOIS, DNS queries) and active (port scanning, service enumeration, OS fingerprinting, banner grabbing).
   - Key actions: `launch_whois_lookup()`, `launch_dns_query()`, `endpoint_scanning(src, dst)`

2. **Infiltration** (`attack_infiltration.ivy`) — Initial access to the target network. Exploit detected vulnerabilities to establish a foothold.

3. **C2 Communication** (`attack_c2_communication.ivy`) — Establish command & control channels for remote control of compromised systems.

**Phase 2: Expansion**
4. **Privilege Escalation** (`attack_privilege_escalation.ivy`) — Gain higher access levels within the compromised network.

5. **Persistence** (`attack_maintain_persistence.ivy`) — Maintain access to the compromised system across reboots and security updates.

**Phase 3: Extraction**
6. **Exfiltration** (`attack_exfiltration.ivy`) — Extract data from the target network.

**Cross-cutting: White Noise** (`attack_white_noise.ivy`) — Distraction attacks to cover the primary attack operation.

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
- **Attacker** — Active adversary initiating attacks
- **Bot** — Compromised system under attacker control
- **C2 Server** — Command & control infrastructure
- **Target** — System being attacked
- **MIM (Man-in-the-Middle)** — Intermediary intercepting communications

Entity definitions reside in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`.

## Protocol-Specific Bindings

Generic APT lifecycle stages are bound to protocol-specific actions through binding directories:

| Protocol | Binding Directory | Description |
|---|---|---|
| QUIC | `quic_apt_lifecycle/` | Maps attacks to QUIC connection manipulation |
| MiniP | `minip_apt_lifecycle/` | Simplified protocol attack bindings |
| UDP | `udp_apt_lifecycle/` | Basic datagram-level attacks |
| Stream Data | `stream_data_apt_lifecycle/` | Stream-oriented attack bindings |

Creating bindings for a new protocol involves mapping each lifecycle stage's generic actions to protocol-specific operations.

## NACT Workflow

### Step 1: Define Threat Model
Identify which APT stages apply to the target protocol. Not all protocols are susceptible to all stages — determine which attacks are relevant.

### Step 2: Design Attack Entities
Define attacker roles and capabilities in `apt_entities/`. Specify what actions each attack entity can perform.

### Step 3: Write Attacker Behavioral Constraints
Create FSM and before/after monitors for attack actions in `apt_entities_behavior/`. Define the valid sequences of attack operations.

### Step 4: Create Protocol-Specific Bindings
Map generic attack stages to protocol-specific actions. Create a `{prot}_apt_lifecycle/` directory with protocol-specific Ivy files.

### Step 5: Write Attack Test Specifications
Create test files in `apt_tests/`:
- `server_attacks/` — Tests attacking server IUTs
- `client_attacks/` — Tests attacking client IUTs
- `mim_attacks/` — Man-in-the-middle attack tests

### Step 6: Verify Attack Specs
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` to verify attack model consistency. Ensure attack specifications are internally coherent.

### Step 7: Compile Attack Tests
Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` to produce attack test executables.

### Step 8: Execute Against IUT
Run attack tests against protocol implementations via PANTHER.

### Step 9: Analyze Security Properties
Check whether the IUT correctly handles each attack scenario. Verify that security properties (confidentiality, integrity, availability) are maintained.

## APT Directory Structure

```
protocol-testing/apt/
├── apt_entities/              # Attack entity definitions
├── apt_entities_behavior/     # Attack entity behavioral constraints
├── apt_lifecycle/             # 6-stage lifecycle definitions
│   ├── attack_life_cycle.ivy  # Master include file
│   ├── attack_reconnaissance.ivy
│   ├── attack_infiltration.ivy
│   ├── attack_c2_communication.ivy
│   ├── attack_privilege_escalation.ivy
│   ├── attack_maintain_persistence.ivy
│   ├── attack_exfiltration.ivy
│   ├── attack_white_noise.ivy
│   ├── quic_apt_lifecycle/    # QUIC-specific bindings
│   ├── minip_apt_lifecycle/   # MiniP-specific bindings
│   └── udp_apt_lifecycle/     # UDP-specific bindings
├── apt_network/               # Attack network infrastructure
├── apt_protocols/             # Protocol-specific APT integration
├── apt_shims/                 # Attack implementation bridges
├── apt_stack/                 # Attack protocol stack layers
├── apt_tests/                 # Attack test specifications
└── apt_utils/                 # Attack utilities
```

## Tools for NACT

Same tools as NCT apply, with focus on navigating the `apt/` directory structure.

### Navigation and editing

Use Claude's built-in tools:
- `Read` — Read file contents
- `Grep` — Search across files
- `Glob` — Find files by pattern
- `Edit` — Modify code in place
- `Write` — Create new files

Native Ivy LSP provides go-to-definition, find-references, hover, and instant diagnostics for `.ivy` files.

### Verification and analysis

Use ivy-tools MCP tools:

| Step | Tool | Usage |
|---|---|---|
| Verify attack model | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` | Check attack spec consistency |
| Compile attack tests | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` | Build attack test executables |
| Inspect model | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` | View attack entity structure |
| Fast structural lint | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` | Quick structural checks |

**IMPORTANT**: Always use ivy-tools MCP tools for Ivy verification operations. Never run ivy_check, ivyc, ivy_show, or ivy_to_cpp directly via Bash.

## Relationship to NCT

NACT and NCT are complementary:
- **NCT** verifies specification compliance (correct behavior)
- **NACT** verifies security properties (resilience to attacks)
- Both use the same Ivy formal language and before/after monitor pattern
- NACT adds attack entity roles and the APT lifecycle framework
- A comprehensive testing campaign uses both NCT and NACT
