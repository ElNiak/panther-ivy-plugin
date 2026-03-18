# When to Use NSCT vs NCT -- Decision Matrix

## Comparison Table

| Criterion | NCT (Real Network) | NSCT (Simulated) |
|---|---|---|
| Fidelity | High (real OS stack) | Medium (simulated stack) |
| Scale | Limited (container resources) | High (many simulated nodes) |
| Determinism | Non-deterministic | Deterministic |
| Topology control | Basic (Docker networks) | Full (arbitrary topologies) |
| Network conditions | Limited manipulation | Full control (latency, loss, bandwidth) |
| Debugging | Harder (non-deterministic) | Easier (deterministic replay) |
| Performance testing | Realistic | Simulated |

## Decision Guide

**Choose NSCT when:**
- Testing under specific network conditions (latency, loss, bandwidth)
- Testing at scale with many simulated nodes
- Needing deterministic reproducibility for debugging
- Exploring complex topologies (meshes, hierarchies, partitions)
- Running regression tests that must be repeatable

**Choose NCT when:**
- Needing realistic network stack behavior
- Testing actual performance characteristics
- Verifying against real-world conditions
- Final validation before deployment

## Recommended Progression

1. **NCT first** -- Verify protocol compliance with real network stack
2. **NACT second** -- Security testing with adversarial entities
3. **NSCT third** -- Scale and condition testing with deterministic simulation

NSCT reuses the same Ivy specifications from NCT. The difference is the execution environment (`type: shadow_ns` vs `type: docker_compose`), not the formal model.
