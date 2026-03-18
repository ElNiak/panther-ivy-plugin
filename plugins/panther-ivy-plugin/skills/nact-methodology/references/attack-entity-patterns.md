# Attack Entity Patterns and Protocol Bindings

## Attack Entity Roles

NACT defines additional entity roles beyond NCT's client/server:

| Entity | Role | Description |
|--------|------|-------------|
| **Attacker** | Active adversary | Initiates attacks, drives the APT lifecycle |
| **Bot** | Compromised system | Under attacker control, executes commands |
| **C2 Server** | Command and control | Infrastructure for remote management |
| **Target** | Victim system | System being attacked |
| **MIM** | Man-in-the-Middle | Intermediary intercepting communications |

Entity definitions reside in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`.

## Entity Definition Pattern

Attack entities follow the same Ivy isolate pattern as NCT entities but model adversarial capabilities:

```ivy
# apt_entities/ivy_attacker.ivy
#lang ivy1.7

object attacker = {
    type this
    individual the_attacker : this

    # Attack state
    relation has_foothold(T:target)
    relation has_c2_channel(C:c2_server)
    relation data_exfiltrated(T:target)

    after init {
        has_foothold(T) := false;
        has_c2_channel(C) := false;
        data_exfiltrated(T) := false;
    }
}
```

## Behavioral Constraint Pattern

Attack behavior uses the same before/after monitor pattern, but from an adversarial perspective:

```ivy
# apt_entities_behavior/ivy_attacker_behavior.ivy
#lang ivy1.7

# NACT monitors model what the attacker CAN do (capabilities),
# not what the protocol SHOULD do (compliance).

before attack_reconnaissance.endpoint_scanning(src, dst) {
    # Attacker must exist and have network access
    require src = attacker.the_attacker;
}

after attack_infiltration.exploit(src, dst, vuln) {
    # Successful exploitation grants foothold
    attacker.has_foothold(dst) := true;
}

after attack_c2_communication.establish_channel(att, c2) {
    # C2 channel established after infiltration
    require attacker.has_foothold(T) for some T:target;
    attacker.has_c2_channel(c2) := true;
}
```

## Protocol-Specific Bindings

Bindings map generic APT lifecycle stages to concrete protocol actions:

| Protocol | Binding Directory | Description |
|----------|-------------------|-------------|
| QUIC | `quic_apt_lifecycle/` | Maps attacks to QUIC connection manipulation |
| MiniP | `minip_apt_lifecycle/` | Simplified protocol attack bindings |
| UDP | `udp_apt_lifecycle/` | Basic datagram-level attacks |
| Stream Data | `stream_data_apt_lifecycle/` | Stream-oriented attack bindings |

### Binding Structure

Each protocol binding directory contains stage-specific mappings:

```
{prot}_apt_lifecycle/
|-- {prot}_reconnaissance.ivy      # Protocol-specific recon actions
|-- {prot}_infiltration.ivy        # Protocol-specific exploitation
|-- {prot}_c2_communication.ivy    # Protocol-specific C2 channels
|-- {prot}_privilege_escalation.ivy
|-- {prot}_persistence.ivy
+-- {prot}_exfiltration.ivy
```

### Example: QUIC Reconnaissance Binding

```ivy
# quic_apt_lifecycle/quic_reconnaissance.ivy
#lang ivy1.7

# Map generic reconnaissance to QUIC-specific actions
after attack_reconnaissance.endpoint_scanning(src, dst) {
    # QUIC Initial packet as probe
    call quic_packet.send_initial(src, dst);
}
```

## Key Difference: NCT vs NACT Monitors

| Aspect | NCT Monitor | NACT Monitor |
|--------|-------------|--------------|
| Perspective | Protocol compliance | Adversarial capability |
| `require` semantics | "Protocol MUST do this" | "Attacker CAN do this if..." |
| State tracking | Connection/stream state | Attack progress, footholds |
| `_finalize` checks | Data transferred, no errors | Attack objectives achieved |
| Entity roles | Client, Server | Attacker, Bot, C2, Target, MIM |
