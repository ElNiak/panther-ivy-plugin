# NSCT Shadow-NS Experiment-Config Template

Consumed by the `scaffold` workflow's Phase 6 Step 1b NSCT sidecar emission. The template is plain YAML wrapped in a fenced code block below; the scaffold workflow's substituter replaces the three placeholder tokens, `mkdir -p`s the target directory under `experiment-config/protocols/{protocol}/`, and writes the substituted content to `experiment_config_{protocol}_shadow.yaml`.

## Placeholders

| Token | Source in `scaffold-state.yaml` | Fallback if absent |
|-------|------------------------------|--------------------|
| `{{protocol}}` | `protocol` | no fallback — this is required |
| `{{version}}` | `decisions['version']` | literal `<fill-in>` |
| `{{test_file_list}}` | `layers` filtered to test specs | `[]` |

## Template (YAML content to write)

```yaml
# NSCT Shadow-NS simulation experiment (scaffold emitted by build Phase 6)
#
# Edit topology, services, and IUT plugin names to your scenario.
# This file is a template intended to be customized; it is not ready-to-run.
#
# Source of truth for canonical experiment-config fields:
# experiment-config/base/experiment_config_example_minimal.yaml

logging:
  level: INFO

tests:
  - name: "{{protocol}} NSCT simulation scaffold"
    network_environment:
      type: shadow_ns
      seed: 42  # deterministic execution; change per scenario
      topology:
        nodes: 2
        links:
          - endpoints: [client, server]
            latency_ms: 0
            loss_percent: 0
            bandwidth_mbps: unlimited
    services:
      client:
        implementation:
          name: <fill-in-iut-plugin-name>
          type: iut
        protocol:
          name: {{protocol}}
          version: {{version}}
          role: client
      server:
        implementation:
          name: <fill-in-iut-plugin-name>
          type: iut
        protocol:
          name: {{protocol}}
          version: {{version}}
          role: server
```

## Post-emission checklist

The scaffold is intentionally minimal. Before invoking `panther run` or `/nct-iut-test` against the emitted file:

1. Replace every `<fill-in-iut-plugin-name>` with a real IUT plugin directory name (e.g., `picoquic`, `frr_bgp`).
2. If the build's target version is known, the substituter already filled `{{version}}`; otherwise replace the literal `<fill-in>` with the protocol version.
3. Adjust `topology.nodes`, `links`, `latency_ms`, `loss_percent`, `bandwidth_mbps` to the scenario. The scaffold's two-node, zero-loss topology is a smoke-test configuration, not a meaningful NSCT simulation.
4. For multi-role scenarios (man-in-the-middle, bot-net), extend the `services` block per the canonical example at `experiment-config/base/experiment_config_example_minimal.yaml` and the NACT-specific entries in `experiment-config/protocols/*/`.

## Drift note

If PANTHER's config schema evolves (new top-level keys, renamed fields, different network-environment type for Shadow-NS), update this template together with `experiment-config/base/experiment_config_example_minimal.yaml` so the scaffold stays consistent with the canonical example.
