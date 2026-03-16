---
name: nsct-methodology
description: "Use when working with NSCT (Network-Simulator Centric Compositional Testing), Shadow Network Simulator, large-scale topology testing, or deterministic network simulation. Covers Shadow NS configuration and when to use NSCT vs NCT."
---

## NSCT -- Network-Simulator Centric Compositional Testing

### Overview

NSCT is a compositional testing methodology that runs protocol verification in simulated network environments using the Shadow Network Simulator. It enables testing at scale with deterministic execution, complex topologies, and controlled network conditions -- complementing NCT's real-network testing.

### Core Concepts

#### Shadow Network Simulator Integration
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

### Red Flags -- STOP

| Rationalization | Reality |
|----------------|---------|
| "I can skip the simulation config" | Without proper topology, your simulation doesn't test what you think it tests. |
| "The same Docker build works for Shadow" | Shadow requires specific build modes. Use the right `build_mode` setting. |
| "Deterministic seeds don't matter for this test" | Determinism is Shadow's key advantage. Always set and document seeds. |
| "I don't need network condition modeling" | If you're not using latency/loss/bandwidth, why use Shadow at all? |

### Common Mistakes

**Wrong build mode**
- **Problem:** Using Docker build mode instead of Shadow-compatible mode
- **Fix:** Use empty string `""` build mode for Shadow NS compatibility

**Missing seed configuration**
- **Problem:** Tests run with random seeds, losing reproducibility
- **Fix:** Always configure `seed` in the experiment YAML for Shadow runs
