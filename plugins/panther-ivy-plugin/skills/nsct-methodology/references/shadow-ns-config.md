# Shadow NS Configuration Deep Dive

## Shadow Network Simulator Integration

Shadow NS provides deterministic network simulation within PANTHER:
- **Deterministic execution** -- Same seed produces identical results, enabling reproducible debugging
- **Scale testing** -- Simulate many nodes simultaneously without real hardware
- **Topology control** -- Define arbitrary network topologies (meshes, hierarchies, partitions)
- **Network condition modeling** -- Simulate latency, packet loss, bandwidth constraints, jitter

## PANTHER Environment Configuration

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

### Key Configuration Sections

**topology.nodes** -- Each node gets a name and IP address. These are the simulated hosts in the Shadow environment.

**topology.links** -- Connections between nodes with network characteristics:
- `latency` -- One-way delay (e.g., `"50ms"`, `"200ms"`)
- `bandwidth` -- Link capacity (e.g., `"10Mbit"`, `"1Gbit"`)
- `loss` -- Packet loss rate (e.g., `"0.1%"`, `"5%"`)

**simulation** -- Global simulation parameters:
- `duration` -- How long the simulation runs
- `seed` -- Integer seed for deterministic execution (critical for reproducibility)

## Shadow NS Build Mode

NSCT requires a specific Z3 build mode for Shadow NS compatibility:
- Use `build_mode: ""` (empty string) in the PANTHER Ivy config
- This uses the legacy `mk_make.py` build system compatible with Shadow NS
- Other build modes (`debug-asan`, `rel-lto`, `release-static-pgo`) are for NCT/NACT Docker environments
