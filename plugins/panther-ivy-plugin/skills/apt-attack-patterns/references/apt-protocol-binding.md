# APT Protocol-Binding Template

How a protocol wires into the APT workspace. Use this as the step-by-step when adding a new protocol under `protocol-testing/apt/`.

## The aggregator

`apt_lifecycle/apt_attack_connection.ivy` is the single include-aggregator for all protocol-specific lifecycle bindings:

```ivy
#lang ivy1.7

include quic_attack_connection
include minip_attack_connection
include malicious_stream_data
```

When you add a new protocol binding, it gets included here.

## Directory shape for a protocol binding

Each per-protocol lifecycle directory sits at `apt_lifecycle/{prot}_apt_lifecycle/`. The canonical file set (using `quic_apt_lifecycle/` as the reference example):

| File | Purpose |
|---|---|
| `{prot}_attack_connection.ivy` | Top-level protocol-under-attack connection model; included from `apt_attack_connection.ivy` |
| `malicious_{prot}_packet.ivy` | `around`-block attack monitors wrapping the base protocol's packet forwarding |
| `malicious_{prot}_frame.ivy` | Attack monitors for frame-level operations |
| `encrypted_{prot}_packet.ivy` | Encrypted-variant attack monitors |
| `encrypted_short_{prot}_packet.ivy` | Short-header / short-form encrypted variant (protocol-specific) |
| `random_padding_encrypted_{prot}_packet.ivy` | Padding-attack variant |

Not every protocol needs every file. Start minimal: `{prot}_attack_connection.ivy` + `malicious_{prot}_packet.ivy` is the irreducible core. Add variants as the threat model demands them.

## Step-by-step: add a new protocol "foo"

1. **Create the directory.** `mkdir protocol-testing/apt/apt_lifecycle/foo_apt_lifecycle/`.
2. **Create the top-level connection file** `foo_attack_connection.ivy`:
   ```ivy
   #lang ivy1.7

   include foo_stack            # base protocol
   include malicious_foo_packet
   include apt_shim

   # Attack-connection model for foo under APT lifecycle.
   ```
3. **Create the malicious-packet file** `malicious_foo_packet.ivy` with `around`-block monitors:
   ```ivy
   #lang ivy1.7
   include foo_packet

   object packet = {
       ...
       object foo_packet = {
           ...
           action forward_to_server(src:ip.endpoint, dst:ip.endpoint, pkt:packet.foo_packet)
           around forward_to_server(...) {
               if _generating {
                   require pkt.payload.end > 0;
                   require mim_agent.nat_configured;
                   # ... attack-specific guards ...
               }
               ...
               if _generating {
                   call enqueue_packet(src, dst, pkt);
               }
           }
       }
   }
   ```
   Mirror `quic_apt_lifecycle/malicious_quic_packet.ivy` for the full pattern (guards, spoofing conditionals, coalescing state updates).
4. **Register with the aggregator.** Add `include foo_attack_connection` to `apt_lifecycle/apt_attack_connection.ivy`.
5. **Add entity variants if needed.** If `foo` requires protocol-specific attacker state, add `apt_entities/foo/ivy_attacker.ivy` etc., following the shape of `apt_entities/quic/` or `apt_entities/minip/`.
6. **Add entity-behavior monitors** under `apt_entities_behavior/` if the new protocol binding needs cross-entity compliance checks.
7. **Verify.** Run `ivy_diagnostics(mode="structural")` on `foo_attack_connection.ivy`, then `ivy_analysis(mode="includes", relative_path=foo_attack_connection.ivy)` to check the include closure resolves cleanly. Finally run `ivy_verify` on a test spec that imports the new binding.
8. **Add a test spec.** Create `apt_tests/foo/{foo}_apt_server_test_<scenario>.ivy` or `_client_test_` following the role-inversion convention (file name describes the IUT being tested, not Ivy's role).

## Extensions to watch for

- **Shim layer.** `apt_shims/foo/foo_shim.ivy` may be needed if the new protocol's IUT wire format differs materially from its pure-Ivy model.
- **Application-protocol binding.** If attackers target an application-layer protocol that runs over `foo` (e.g. HTTP over foo for covert C2), add `apt_protocols/{app_proto}/` rather than extending `malicious_foo_packet.ivy`.
- **Stack layer.** `apt_stack/` hosts composition of the above under the APT 14+4 layer template. New protocols usually do not add to `apt_stack/` directly; the aggregator pulls via `apt_attack_connection.ivy`.

## Per-protocol lifecycle binding (overview)

`apt_lifecycle/apt_attack_connection.ivy` is a one-file aggregator that includes the per-protocol lifecycle files:

```ivy
#lang ivy1.7
include quic_attack_connection
include minip_attack_connection
include malicious_stream_data
```

Each protocol-specific subdirectory (`quic_apt_lifecycle/`, `minip_apt_lifecycle/`, `udp_apt_lifecycle/`, `stream_data_apt_lifecycle/`) contains malicious variants of that protocol's packets, frames, and connection layer. For example, `quic_apt_lifecycle/` holds `malicious_quic_packet.ivy`, `malicious_quic_frame.ivy`, `encrypted_quic_packet.ivy`, `encrypted_short_quic_packet.ivy`, `random_padding_encrypted_quic_packet.ivy`, `quic_attack_connection.ivy`.

**Rule.** When adding a new protocol to the APT workspace, create an `apt_lifecycle/{prot}_apt_lifecycle/` directory, mirror the required variants (packet, frame, connection), and include the new aggregate in `apt_attack_connection.ivy`.

**Why:** Mirroring the variant set per protocol lets the test generator reuse a single scaffolding strategy across protocols; the aggregate include in `apt_attack_connection.ivy` is the only hook the lifecycle orchestrator needs to consume the new protocol.

## Attack around-block monitors

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

**Why:** Reusing the underlying type means the existing serializer, monitors, and verification machinery accept malicious instances unchanged; redefining types would force a parallel verification stack and would break the assume-guarantee boundary that NCT compliance relies on.

## Attack entities and parameters

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

**Why:** Localising knobs to the entity that owns the behaviour keeps attack invariants adjacent to the state they constrain. Cross-entity sprinkling complicates G2 modeling-gate verdicts and forces reviewers to chase the same parameter across multiple files when reasoning about a single attack mode.

## Application-layer attack bindings

`apt_protocols/` contains attack-context bindings for application-layer protocols that ride over the primary transport: `tls/`, `http/`, `smtp/`, `dns/`, `quic/`, `minip/`. A binding provides monitor hooks for the application protocol's behavior under attacker perspective (e.g. DNS tunneling for exfiltration, HTTP covert channels for C2).

**Rule.** When modeling a new exfiltration or C2 channel on a new application protocol, add `apt_protocols/{new_prot}/` with the same shape as an existing binding. Do not modify the base application-protocol stack; all attack awareness lives under `apt_protocols/`.

**Why:** Keeping attack awareness above the base stack means the same compliance model verifies both attacker-context and benign-context invariants without forcing a NACT/NCT branch into the layer graph; the base stack stays reusable for pure NCT.
