---
name: methodology-reference
description: "Use when working with NCT (compositional protocol testing), NACT (attack testing, security testing, APT lifecycle), or NSCT (simulation, Shadow NS, large-scale testing) methodology. Covers all three PANTHER formal testing methodologies."
---

<HARD-GATE>
Do NOT write any specification code until you have completed Phase 1 (Explore) and
Phase 2 (Plan) via the ivy-workflow-orchestrator skill.
</HARD-GATE>

# PANTHER Formal Testing Methodologies

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This is the authoritative reference for all three PANTHER formal testing methodologies: NCT, NACT, and NSCT. All three share the same Ivy formal specification language, 14-layer template, and before/after monitor pattern. They differ in execution environment and testing focus.

---

## NCT -- Network-Centric Compositional Testing

NCT is a specification-based testing methodology where a formal Ivy protocol specification plays one role (client, server, or man-in-the-middle) against an Implementation Under Test (IUT). The specification generates test traffic via Z3/SMT symbolic execution and monitors received packets against formal assertions. NCT uses real Docker network environments for high-fidelity protocol testing.

For full workflow steps, directory structure, red flags, and common mistakes, see `references/comprehensive-methodology-detail.md`.

## NACT -- Network-Attack Compositional Testing

NACT extends NCT to model and test protocols from an attacker's perspective using the APT (Advanced Persistent Threat) 6-stage lifecycle. Attack specifications use the same Ivy formal language and before/after monitor pattern as NCT but focus on adversarial behavior -- modeling what an attacker CAN do rather than what the protocol SHOULD do. NACT adds attack entity roles (Attacker, Bot, C2 Server, Target, MIM) and protocol-specific attack bindings.

For full APT lifecycle detail, attack entities, protocol bindings, red flags, and common mistakes, see `references/comprehensive-methodology-detail.md`.

## NSCT -- Network-Simulator Centric Compositional Testing

NSCT runs the same Ivy specifications in simulated network environments using the Shadow Network Simulator instead of real Docker networks. It enables testing at scale with deterministic execution, complex topologies, and controlled network conditions (latency, loss, bandwidth). NSCT complements NCT's real-network testing with reproducible, large-scale verification.

For full Shadow NS configuration, workflow steps, red flags, and common mistakes, see `references/comprehensive-methodology-detail.md`.

---

## When to Use Which

| Criterion | NCT | NACT | NSCT |
|---|---|---|---|
| **Goal** | Specification compliance | Security resilience | Scale and conditions |
| **Environment** | Docker (real network) | Docker (real network) | Shadow NS (simulated) |
| **Perspective** | Compliant peer | Adversary (APT lifecycle) | Compliant peer |
| **Fidelity** | High (real OS stack) | High (real OS stack) | Medium (simulated stack) |
| **Determinism** | Non-deterministic | Non-deterministic | Deterministic (seed-controlled) |
| **Scale** | Limited (containers) | Limited (containers) | High (many simulated nodes) |
| **Topology control** | Basic (Docker nets) | Basic (Docker nets) | Full (arbitrary topologies) |
| **Network conditions** | Limited | Limited | Full control |
| **Use when** | Verifying RFC compliance | Testing attack resilience | Testing under adverse/scaled conditions |

**Recommended order**: NCT first (compliance) -> NACT second (security) -> NSCT third (scale/conditions).

---

## Core Concepts

### Role Inversion (NCT/NACT)

The Ivy tester's role is the **opposite** of what it tests. Testing a server IUT means Ivy acts as a formal client; testing a client means Ivy acts as a formal server. File naming follows what is tested, not what Ivy plays: `{prot}_server_test_*.ivy` tests the server (Ivy plays client). MIM testing uses `{prot}_mim_test_*.ivy` where Ivy intercepts traffic between both roles. This inversion applies to both NCT (compliance) and NACT (attack) methodologies.

### APT Lifecycle (NACT)

NACT organizes attacks into three phases with six stages: Infiltration (Reconnaissance, Infiltration, C2 Communication), Expansion (Privilege Escalation, Persistence), and Extraction (Exfiltration), plus a cross-cutting White Noise stage for distraction. The master file `attack_life_cycle.ivy` composes all stages. Each stage maps to protocol-specific bindings in `{prot}_apt_lifecycle/` directories. Attack entities (Attacker, Bot, C2 Server, Target, MIM) are defined in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`.

### Shadow Network Simulator (NSCT)

Shadow NS provides deterministic network simulation: same seed produces identical results, enabling reproducible debugging. Configure topologies with arbitrary nodes and links, specifying latency, bandwidth, and loss per link. Use `type: shadow_ns` in PANTHER experiment config and `build_mode: ""` (empty string) for Shadow-compatible Z3 builds. The same Ivy specifications from NCT/NACT are reused without modification -- only the execution environment changes.

### Shared Specification Foundation

All three methodologies share the same Ivy formal language, 14-layer template, and before/after monitor pattern (before clauses for preconditions/guards, after clauses for state updates/checks, `_finalize()` for end-state verification, `export` for test mirror generation). Specifications are written once and deployed across NCT, NACT, and NSCT contexts.

---

## Integration
- **CHAINS TO:** ivy-workflow-orchestrator (for all spec creation/modification)
- **LOADS:** ivy-toolkit (for tool operations)
- **RELATED SKILLS:** nct-methodology, nact-methodology, nsct-methodology (methodology-specific detail)
- **DISPATCHES:** methodology-guide agent (for interactive guidance)

## Reference Files
- **references/comprehensive-methodology-detail.md** -- Full workflow steps, red flags, and common mistakes for all three methodologies
