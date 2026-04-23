# Attack-Stage File Examples

Verbatim excerpts from files at `protocol-testing/apt/apt_lifecycle/` — the 6 sequential APT stages plus the cross-cutting `attack_white_noise.ivy` and top-level `attack_life_cycle.ivy` aggregator. These files are intentionally thin: they provide action-stub scaffolding plus threat-model rationale in comments. Real attack logic lives in per-protocol bindings under `apt_lifecycle/{prot}_apt_lifecycle/`.

## Stage 1 — Reconnaissance (`attack_reconnaissance.ivy`)

```ivy
#lang ivy1.7

# Reconnaissance: In this first stage, attackers collect information about the
# target organization by investigating its infrastructure, employees, partners,
# or customers. They may employ open-source intelligence (OSINT), social
# engineering tactics, or exploit known vulnerabilities in publicly accessible systems.

# 1. Passive Reconnaissance
#     Description: Gathering information without directly interacting with the target.
action launch_whois_lookup = {}
action launch_dns_query = {}

# 2. Active Reconnaissance
#     Description: Directly interacting with the target's systems to gather information.
action endpoint_scanning(src:ip.endpoint, dst:ip.endpoint) = {}
```

Notes:
- Empty action bodies (`= {}`) are the canonical stub form. Protocol-specific bindings fill them in.
- Comments carry the threat-model taxonomy (OSINT subtypes, active vs. passive scan).
- Action signatures match the underlying protocol's endpoint types (`ip.endpoint`) for later composition.

## Stage 3 — C2 Communication (`attack_c2_communication.ivy`)

```ivy
#lang ivy1.7

include apt_packet

# Stage 3: Establish a Foothold

# After breaching an IT ecosystem, cybercriminals then deploy trojan malware that
# establishes a series of backdoor connections to criminal servers (command and
# control servers) to facilitate the exfiltration of sensitive data.

action start_c2_communication = { }
action stop_c2_communication = { }
```

Notes:
- `include apt_packet` brings in the APT packet abstraction shared across stages.
- Action names are verbs in imperative form (`start_*`, `stop_*`).

## Stage 6 — Exfiltration (`attack_exfiltration.ivy`)

```ivy
#lang ivy1.7

# Stage 6: Exfiltrate Data

# When hackers discover valuable information, it's transferred through the
# backdoors established in stage 3 and into their servers. This usually transpires
# alongside legitimate network processes to mitigate suspicious network activity spikes.

action start_exfiltration = { }
action stop_exfiltration = { }
action eavedrop = { }
action covert_channel = { }
```

Notes:
- Multiple action stubs per stage are fine when the stage has distinct sub-behaviors (start / stop / passive eavesdrop / covert channel).
- The typo `eavedrop` (should be `eavesdrop`) is preserved verbatim for the pattern match — do not silently rename it; file an action-rename task instead if the typo blocks something.

## Adding a new stage file

1. Create `apt_lifecycle/attack_<stage>.ivy`.
2. Copy the `#lang ivy1.7` header and any required `include` directive.
3. Add a multi-paragraph comment block explaining the stage's threat-model role. Cite MITRE ATT&CK or the primary reference if one applies.
4. Declare one or more action stubs with empty bodies. Name them with imperative verbs.
5. Reference the new file from `attack_life_cycle.ivy` if the stage participates in the top-level lifecycle composition.
6. Run `ivy_diagnostics(mode="structural")` on the new file to confirm no structural errors before adding protocol-specific bindings.
