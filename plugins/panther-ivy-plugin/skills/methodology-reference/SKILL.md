---
name: methodology-reference
description: "Hub for NCT, NACT, and NSCT formal testing methodologies. Use when the user asks about testing methodology, wants to choose between methodologies, or mentions formal protocol testing without specifying which methodology."
allowed-tools: "Read Grep Glob ToolSearch"
loads: [nct-methodology, nact-methodology, nsct-methodology, ivy-toolkit]
---

# Formal Testing Methodologies

## Methodology Selection

| Methodology | Purpose | When to Use | Skill |
|-------------|---------|-------------|-------|
| **NCT** | Specification-based compliance testing | Testing protocol implementations against RFCs | `nct-methodology` |
| **NACT** | Adversarial security testing | Testing resistance to APT-style attacks | `nact-methodology` |
| **NSCT** | Simulation-based testing | Testing under controlled network conditions | `nsct-methodology` |

## Shared Foundations

All three methodologies share:
- **14-layer specification template** (see `specification-patterns`)
- **Before/after monitor pattern** for behavioral assertions
- **`require`/`export`/`_finalize` semantics** for invariant enforcement
- **Role inversion** (Ivy tester acts as the opposite role of the IUT)

## Quick Decision Tree

1. **Testing RFC compliance?** → NCT (`nct-methodology`)
2. **Testing security against attacks?** → NACT (`nact-methodology`)
3. **Testing under network conditions?** → NSCT (`nsct-methodology`)
4. **Not sure?** → Start with NCT (the foundation for both NACT and NSCT)

For tool usage across all methodologies, see `ivy-toolkit`.
