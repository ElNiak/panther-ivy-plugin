---
name: apt-attack-patterns
description: "APT-layer pattern library for NACT: 6-stage attack lifecycle plus cross-cutting and aggregator files, attack entities (Attacker / Bot / C2 / Target / MIM), protocol bindings under apt_lifecycle/, and around-block attack monitors. Use when authoring or extending attack specifications under protocol-testing/apt/."
user-invocable: false
context: fork
---

# APT Attack Patterns

NACT (Network-Attack Compositional Testing) extends NCT with attacker perspective. The APT workspace at `protocol-testing/apt/` mirrors the 14-layer NCT template and adds four attack-specific layers. This skill catalogues the reusable structural patterns across those layers; the canonical methodology overview lives in `methodology-reference` and `.claude/rules/nct-methodology.md`.

## When this applies

You are editing a file under `protocol-testing/apt/` (any of `apt_entities/`, `apt_entities_behavior/`, `apt_lifecycle/`, `apt_protocols/`, `apt_shims/`, `apt_stack/`, or `apt_tests/`), or you are scaffolding a new attack-stage file, malicious-variant packet, or protocol binding.

## Four extra APT layers

APT builds on the 14-layer NCT template (see `specification-patterns`) and adds these layers:

| APT layer | Location | Purpose |
|---|---|---|
| Attack entities | `apt_entities/*.ivy` (+ per-protocol subdirs) | Attacker, Bot, C2 Server, Target, MIM definitions and parameters |
| Attack entity behavior | `apt_entities_behavior/` | Before/after monitors applied to attack entities |
| Attack lifecycle | `apt_lifecycle/attack_*.ivy` + per-protocol `apt_lifecycle/{prot}_apt_lifecycle/` | 6 lifecycle stages + `attack_white_noise.ivy` (cross-cutting) + `attack_life_cycle.ivy` (top-level aggregator), plus protocol-specific malicious variants |
| Attack-aware application protocols | `apt_protocols/{tls,http,smtp,dns,quic,minip}/` | Attack-context bindings for application-layer protocols |

Each layer follows one core invariant: attack behavior extends, never replaces, the underlying NCT protocol model. A malicious packet is still a packet; the attack layer adds guards and generator bias, not new types.

## Pattern 1 — 6-stage attack-lifecycle scaffolding

The APT lifecycle in `.claude/rules/nct-methodology.md` defines **six sequential stages** (Reconnaissance → Infiltration → C2 Communication → Privilege Escalation → Maintain Persistence → Exfiltration). `apt_lifecycle/` holds one file per stage plus two supporting files: `attack_white_noise.ivy` for cross-cutting background traffic (not a stage; runs alongside any stage), and `attack_life_cycle.ivy` as the top-level aggregator. All are deliberately thin — action stubs plus rationale comments — with real behavior in per-protocol bindings under `apt_lifecycle/{prot}_apt_lifecycle/`.

| # | Role | File | Canonical content |
|---|---|---|---|
| 1 | Stage — Reconnaissance | `attack_reconnaissance.ivy` | `action launch_whois_lookup`, `action launch_dns_query`, `action endpoint_scanning` |
| 2 | Stage — Infiltration | `attack_infiltration.ivy` | Infiltration-stage action stubs |
| 3 | Stage — C2 Communication | `attack_c2_communication.ivy` | `action start_c2_communication`, `action stop_c2_communication` |
| 4 | Stage — Privilege Escalation | `attack_privilege_escalation.ivy` | Privilege-escalation stubs |
| 5 | Stage — Maintain Persistence | `attack_maintain_persistence.ivy` | Persistence stubs |
| 6 | Stage — Exfiltration | `attack_exfiltration.ivy` | Exfiltration stubs |
| — | Cross-cutting | `attack_white_noise.ivy` | Background-traffic generation |
| — | Aggregator | `attack_life_cycle.ivy` | Top-level lifecycle composition |

**Rule.** When adding a new attack-stage file, follow the existing pattern: include `#lang ivy1.7`, include any required apt-layer files at the top, define action stubs with one-line docstrings, and leave protocol-specific implementation to the per-protocol bindings. See `references/attack-stage-examples.md` for verbatim excerpts.

## Pattern 2 — Per-protocol lifecycle binding

`apt_lifecycle/apt_attack_connection.ivy` is a one-file aggregator that includes the per-protocol lifecycle files:

```ivy
#lang ivy1.7
include quic_attack_connection
include minip_attack_connection
include malicious_stream_data
```

Each protocol-specific subdirectory (`quic_apt_lifecycle/`, `minip_apt_lifecycle/`, `udp_apt_lifecycle/`, `stream_data_apt_lifecycle/`) contains malicious variants of that protocol's packets, frames, and connection layer. For example, `quic_apt_lifecycle/` holds `malicious_quic_packet.ivy`, `malicious_quic_frame.ivy`, `encrypted_quic_packet.ivy`, `encrypted_short_quic_packet.ivy`, `random_padding_encrypted_quic_packet.ivy`, `quic_attack_connection.ivy`.

**Rule.** When adding a new protocol to the APT workspace, create an `apt_lifecycle/{prot}_apt_lifecycle/` directory, mirror the required variants (packet, frame, connection), and include the new aggregate in `apt_attack_connection.ivy`. See `references/apt-protocol-binding.md` for the full step-by-step.

## Pattern 3 — Attack around-block monitors

The core NACT generation pattern wraps normal protocol actions (from `quic_stack/`, `minip_stack/`, etc.) with `around` blocks that add attacker-specific guards. Example from `malicious_quic_packet.ivy`:

```ivy
action forward_to_client(src:ip.endpoint, dst:ip.endpoint, pkt:packet.quic_packet)
around forward_to_client(src:ip.endpoint, dst:ip.endpoint, pkt:packet.quic_packet) {
    if _generating {
        require pkt.payload.end > 0;
        require mim_agent.nat_configured;
        require is_quic_packet_received(dst, pkt, ...);
        require src ~= dst;
        if spoof_server_ip {
            require src = mim_agent.ep_mim & dst = mim_agent.ep_client;
        } else {
            require src = mim_agent.ep_server & dst = mim_agent.ep_client;
        }
    }
    ...
    if _generating {
        call enqueue_packet(src, dst, pkt);
        ...
    }
}
```

**Rule.** Attack monitors never modify the underlying type (a `quic_packet` stays a `quic_packet`). They add `_generating`-gated `require` clauses that encode attacker knowledge, entity role (`mim_agent`, `ep_client`, `ep_server`), and attack-specific invariants (NAT spoofing, packet coalescing, MIM positioning). Actions are typically structured as pairs (`forward_to_client` / `forward_to_server`) to let the test generator pick the attacker's direction.

## Pattern 4 — Attack entities and parameters

`apt_entities/` has a root file per core entity and per-protocol variant subdirectories:

| File | Role |
|---|---|
| `ivy_attacker.ivy` | Root attacker definition: `malicious_client_addr`, `malicious_client_port`, `is_scanning`, `slow_loris`, scanning parameters |
| `ivy_bot.ivy` | Bot agent |
| `ivy_c2_server.ivy` | Command-and-control server |
| `ivy_target.ivy` | Target under attack |
| `ivy_mim.ivy` | Man-in-the-middle agent |
| `ivy_client.ivy` / `ivy_server.ivy` | Legitimate participants, re-exposed for attack-context composition |

Each entity file declares `parameter` knobs for address, port, and attack-specific behavior (scanning, timeouts, slow-loris, spoofing flags). Entity files have a sibling `.md` that documents the attacker model (capabilities, assumptions, references to threat-model literature).

Per-protocol directories under `apt_entities/` (e.g. `apt_entities/quic/`, `apt_entities/minip/`) extend the root entities with protocol-specific state, and `apt_entities_behavior/` hosts the `before` / `after` monitors that implement entity-scoped compliance checks in the attack context.

**Rule.** When introducing a new attack knob (e.g. a timing-based attack parameter), add the `parameter` to the most-specific entity that owns it. Avoid sprinkling parameters across multiple entities unless the knob is genuinely cross-cutting.

## Pattern 5 — Application-layer attack bindings

`apt_protocols/` contains attack-context bindings for application-layer protocols that ride over the primary transport: `tls/`, `http/`, `smtp/`, `dns/`, `quic/`, `minip/`. A binding provides monitor hooks for the application protocol's behavior under attacker perspective (e.g. DNS tunneling for exfiltration, HTTP covert channels for C2).

**Rule.** When modeling a new exfiltration or C2 channel on a new application protocol, add `apt_protocols/{new_prot}/` with the same shape as an existing binding. Do not modify the base application-protocol stack; all attack awareness lives under `apt_protocols/`.

## How NACT diverges from NCT

Three operational differences to keep in mind:

1. **Generator bias.** NACT test generation uses the same `_generating` guard pattern as NCT but weights generator actions toward attacker behavior (spoofed packets, malicious frames, coalesced deliveries). Weight attributes on attack actions typically sit much higher than on legitimate actions.
2. **Role inversion still applies.** Testing an IUT server means Ivy plays a malicious client (or MIM, depending on the attack stage). File naming convention is the same: `{prot}_server_attack_*.ivy` tests an IUT server from the attacker's perspective.
3. **Verification scope.** `ivy_verify` on attack specs verifies attacker-side invariants (what an attacker *can* send while staying within the spec), not IUT defender invariants. Counterexamples here mean the attacker is *unable* to reach a state the model claims should be reachable.

## Integration

- **LOADED BY:** build workflow (Phase 3 Write when the target file path contains `protocol-testing/apt/`); verify workflow (Phase 6 Diagnose when a failure traces to attack-entity or lifecycle logic).
- **LOADS:** the reference files below for concrete code excerpts and the protocol-binding template.

**Related skills:**
- **`specification-patterns`** — the base 14-layer template; APT extends it.
- **`methodology-reference`** — NCT / NACT / NSCT selection and methodology-level guidance.
- **`ivy-writing-guide`** — Ivy syntax for `around` blocks, `parameter` declarations, and include directives.
- **`ivy-toolkit`** — tool invocations, especially `ivy_analysis(mode="includes")` for tracing APT include closure.

## References

- `references/attack-stage-examples.md` — verbatim excerpts from three stage files (reconnaissance, c2_communication, exfiltration) showing the stub-file convention.
- `references/apt-protocol-binding.md` — step-by-step template for adding a new protocol under `apt_lifecycle/{prot}_apt_lifecycle/`.
