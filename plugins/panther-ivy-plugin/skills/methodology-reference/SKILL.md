---
name: methodology-reference
description: "Use when working with NCT (compositional protocol testing), NACT (attack testing, security testing, APT lifecycle), or NSCT (simulation, Shadow NS, large-scale testing) methodology. Covers all three PANTHER formal testing methodologies."
---

# PANTHER Formal Testing Methodologies

This skill provides an overview of all three PANTHER formal testing methodologies: NCT, NACT, and NSCT. All three share the same Ivy formal specification language, 14-layer template, and before/after monitor pattern. They differ in execution environment and testing focus.

For detailed guidance on a specific methodology, use the dedicated sub-skill:

- **`nct-methodology`** -- NCT (Network-Centric Compositional Testing): specification-based protocol compliance testing with Ivy formal models. Covers the 10-step NCT workflow, test traffic generation, role inversion, directory structure, and common mistakes.

- **`nact-methodology`** -- NACT (Network-Attack Compositional Testing): security and attack testing using the APT 6-stage lifecycle. Covers attack entities, protocol-specific bindings, threat model definition, and adversarial monitors.

- **`nsct-methodology`** -- NSCT (Network-Simulator Centric Compositional Testing): large-scale simulation testing with Shadow Network Simulator. Covers deterministic execution, topology control, network condition modeling, and Shadow NS configuration.

---

## Comprehensive Testing Strategy

A complete protocol verification campaign combines all three methodologies:

1. **NCT first** -- Verify basic specification compliance with real network
2. **NACT second** -- Test resilience against attack scenarios
3. **NSCT third** -- Verify behavior at scale and under adverse conditions

Each methodology shares the same Ivy formal specifications but applies them in different execution contexts, providing comprehensive coverage of protocol correctness, security, and robustness.

## Integration

**Related agents:**
- **methodology-guide** -- Interactive methodology workflow execution
- **spec-analyst** -- Specification navigation and verification
- **traceability-agent** -- RFC requirement extraction and coverage review

**Related skills:**
- **specification-patterns** -- 14-layer template and formal model patterns
- **ivy-writing-guide** -- Ivy language reference for writing specs
- **workflow-reference** -- RFC-to-Ivy mapping, verification, quality gates

**Related commands:**
- `/nct-check` -- Quick verification
- `/nct-compile` -- Compilation
- `/nct-scaffold` -- Protocol and test scaffolding
