---
name: nsct-methodology
description: "Use when working with NSCT (Network-Simulator Centric Compositional Testing), Shadow Network Simulator, large-scale topology testing, or deterministic network simulation. Covers Shadow NS configuration and when to use NSCT vs NCT."
prerequisites:
  - nct-methodology
---

<HARD-GATE>
Do NOT create simulation configurations or topology definitions until you have
completed Phase 1 (Explore) and Phase 2 (Plan) via the ivy-workflow-orchestrator skill.
</HARD-GATE>

## Iron Laws
1. NO SIMULATION CONFIG without completed topology design
2. NO EXECUTION without validated configuration
3. ALWAYS chain to ivy-workflow-orchestrator for simulation setup
4. ALWAYS use ivy-toolkit for tool operations (never direct CLI)

## NSCT -- Network-Simulator Centric Compositional Testing

### Overview

NSCT is a compositional testing methodology that runs protocol verification in simulated network environments using the Shadow Network Simulator. It enables testing at scale with deterministic execution, complex topologies, and controlled network conditions -- complementing NCT's real-network testing.

Same Ivy specs, different execution environment: Shadow NS instead of real Docker networks. Provides deterministic execution (seed-controlled), scale testing (many nodes), topology control, and network condition modeling (latency, loss, bandwidth).

**Recommended progression:** NCT first (compliance) -> NACT second (security) -> NSCT third (scale/conditions).

### Core Concepts

- **Deterministic execution** -- Same seed produces identical results for reproducible debugging
- **Scale testing** -- Simulate many nodes without real hardware
- **Topology control** -- Define arbitrary network topologies (meshes, hierarchies, partitions)
- **Network condition modeling** -- Simulate latency, packet loss, bandwidth constraints, jitter
- **Spec reuse** -- NSCT reuses the same Ivy specifications from NCT; the difference is the execution environment (`type: shadow_ns` vs `type: docker_compose`), not the formal model

### NSCT Phase Specializations

NSCT follows the same phased workflow as NCT but with key replacements:

| Phase | NCT | NSCT Replacement |
|---|---|---|
| Phase 2 (PLAN) | 14-layer decomposition | **Topology design** -- nodes, links, latencies, bandwidths, loss rates |
| Phase 3 (WRITE) | Ivy specification writing | **Shadow NS YAML config** -- `type: shadow_ns` experiment configuration |
| Phase 4 (VERIFY) | `ivy_verify` + `ivy_compile` | Same verification + **simulation parameter validation** |
| Phase 5 (FINALIZE) | Docker Compose execution | **Shadow NS simulation** -- `panther run --config <config.yaml>` |

### NSCT Workflow

> **Workspace**: Before starting, set the active workspace with `/set-workspace <protocol>` to ensure edit isolation and correct include resolution.

1. **Define network topology** -- nodes, links, latencies, bandwidths, loss rates
2. **Configure simulation parameters** -- duration, seed, logging level
3. **Map IUT implementations to simulated nodes** -- set up protocol implementations
4. **Reuse Ivy formal specifications** -- same specs from NCT (no rewrite needed)
5. **Write PANTHER experiment config** -- YAML with `type: shadow_ns` (see `references/shadow-ns-config.md`)
6. **Execute simulation** -- `panther run --config <config.yaml>`
7. **Analyze results** -- examine simulation logs and verification output
8. **Iterate** -- modify topology, latency, loss rates, bandwidth and re-run

### Shadow NS Build Mode

NSCT requires a specific Z3 build mode for Shadow NS compatibility:
- Use `build_mode: ""` (empty string) in PANTHER Ivy config
- This uses the legacy `mk_make.py` build system compatible with Shadow NS
- Other build modes (`debug-asan`, `rel-lto`, `release-static-pgo`) are for NCT/NACT Docker environments

### Checkpoints -- Verify Before Continuing

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Topology design complete | Phase 2 must produce a validated node/link topology before any config writing. |
| Simulation config defined | Proper topology ensures the simulation tests what you intend. |
| Correct build mode selected | Shadow requires `build_mode: ""` -- other modes are for NCT/NACT Docker environments. |
| Deterministic seed configured | Reproducibility is Shadow's key advantage. Always set and document seeds. |
| Network conditions modeled | Latency/loss/bandwidth modeling is the reason to use Shadow over Docker. |
| Configuration validated | Run `panther config validate --config <file>` before execution. |

### Common Mistakes

**Wrong build mode**
- **Convention:** Match the build mode to your execution environment
- **Rule:** Use empty string `""` build mode for Shadow NS compatibility; other modes are for NCT/NACT Docker environments

**Missing seed configuration**
- **Problem:** Tests run with random seeds, losing reproducibility
- **Fix:** Always configure `seed` in the experiment YAML for Shadow runs

**Skipping topology design**
- **Problem:** Jumping directly to YAML config without planning node layout and link characteristics
- **Fix:** Complete Phase 2 topology design via ivy-workflow-orchestrator before writing config

**Using NCT Docker environment by accident**
- **Problem:** Config uses `type: docker_compose` instead of `type: shadow_ns`
- **Fix:** Verify the `network_environment.type` field is set to `shadow_ns`

## Integration
- **CHAINS TO:** ivy-workflow-orchestrator (for deep mode -- simulation setup)
- **LOADS:** ivy-toolkit (for all tool operations)
- **PREREQUISITE:** nct-methodology (NSCT wraps NCT specs in simulation)
- **FAST MODE:** For concept questions about NSCT/Shadow NS, use this skill directly
- **DEEP MODE:** For simulation setup, invoke ivy-workflow-orchestrator

## Reference Files
- **references/shadow-ns-config.md** -- Shadow NS configuration deep dive
- **references/nct-vs-nsct-comparison.md** -- When to use NCT vs NSCT decision matrix
