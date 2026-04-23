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
