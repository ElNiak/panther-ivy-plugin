---
name: knowledge-methodology-reference
description: "Use when choosing a testing methodology, starting model construction, or mapping RFC requirements to an Ivy testing strategy. Provides NCT (compliance) / NACT (security) / NSCT (simulation) selection and workflow guidance."
user-invocable: false
---

# Formal Testing Methodologies

**Type:** flexible — adapt principles to context.

## Methodology Selection

| Methodology | Purpose | When to Use |
|-------------|---------|-------------|
| **NCT** | Specification-based compliance testing | Testing protocol implementations against RFCs |
| **NACT** | Adversarial security testing | Testing resistance to APT-style attacks |
| **NSCT** | Simulation-based testing | Testing under controlled network conditions |

## Shared Foundations

All three methodologies share:

- **14-layer specification template** — canonical table location is documented in `.claude/rules/nct-methodology.md`; optional-layer discussion and scaffolding decisions live in `specification-patterns`.
- **Before/after monitor pattern** for behavioral assertions.
- **`require` / `export` / `_finalize` semantics** for invariant enforcement.
- **Role inversion** (Ivy tester acts as the opposite role of the IUT).

## Quick Decision Tree

1. **Testing RFC compliance?** → NCT
2. **Testing security against attacks?** → NACT
3. **Testing under network conditions?** → NSCT
4. **Not sure?** → Start with NCT (the foundation for both NACT and NSCT)

For tool usage across all methodologies, see `ivy-toolkit`.

### Dispatch decision table

Once the methodology is chosen, this table maps the user's situation to the first skill and workflow to load.

| Situation | Methodology | First skill to load | First workflow |
|---|---|---|---|
| RFC compliance test, IUT exists | NCT | `knowledge-specification-patterns` | `workflow-build` |
| Attack / security test, attacker model needed | NACT | `knowledge-apt-attack-patterns` | `workflow-build` |
| Network-condition / replay tests (Shadow simulator) | NSCT | `knowledge-methodology-reference` (this file) | `workflow-build` |
| Existing spec, want to verify | (any) | `knowledge-verification-failures` | `workflow-verify` |
| Existing spec, want coverage / quality verdict | (any) | `knowledge-verification-failures` | `workflow-review` |
| Tools timing out / MCP errors | (any) | (none — direct invocation) | `workflow-triage` |

For an end-to-end NCT walkthrough on a QUIC server IUT (workspace setup, methodology detection, layer scaffolding, role inversion, G3 / G4 / G5 gates, and the build ↔ verify hand-off via `pending_dispatch`), Read `references/walkthrough-nct-quic-server.md`. For the calibrated meanings of NCT / NACT / NSCT / isolate / monitor / `_finalize` / role inversion / `export` / `import`, Read `references/glossary.md`.

---

## NCT

For the full 10-step NCT workflow, role-inversion semantics, specification structure (before / after / `_finalize`), test-traffic generation via `export`, failure patterns, and the verification-checkpoint cycle, Read `references/comprehensive-methodology-detail.md`.

### Directory Structure

```
protocol-testing/{prot}/
|-- {prot}_stack/          # Core protocol model (layers 1-9)
|-- {prot}_entities/       # Entity definitions and behavior
|-- {prot}_shims/          # Implementation bridge
|-- {prot}_utils/          # Serialization, utilities
+-- {prot}_tests/
    |-- server_tests/      # Tests targeting server IUTs
    |-- client_tests/      # Tests targeting client IUTs
    +-- mim_tests/         # Man-in-the-middle tests
```

**Naming**: `{prot}_{layer}.ivy` for stack layers, `ivy_{prot}_{role}.ivy` for entities, `{prot}_{role}_test_*.ivy` for tests.

### NCT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Type layer complete | All other layers depend on type definitions being in place first. |
| Verification passes | Verify after every meaningful change — errors compound when deferred. |
| RFC consulted | RFC is the source of truth for every requirement and assertion. |
| Bracket tags present | Every assertion has a `# [rfcNNNN:X.Y]` tag for traceability. |
| Role inversion correct | Testing a server = Ivy acts as client; file names reflect what is tested. |
| `_finalize` exported | End-state properties require `_finalize` to execute. |

### Common NCT Mistakes

See the `ivy-error-patterns` skill for the full error-to-fix lookup table. Most frequent NCT-specific mistakes:

- Missing `after init` (error pattern #12) — relations start with arbitrary values.
- Ungrounded variables (error pattern #2) — `invariant sent(P,N)` means "for ALL P, N".
- Missing bracket tags — tag every assertion with `# [rfcNNNN:X.Y]`.
- Missing `export _finalize` — end-state checks never execute.
- Wrong role assignment — file name indicates WHAT IS TESTED (server test = Ivy plays client).

---

## NACT

For the concrete pattern library backing NACT (APT 6-stage lifecycle, stage-file scaffolding, attack-entity composition, protocol-binding template, `around`-block monitors), load the `apt-attack-patterns` skill via the `Skill` tool.

### NACT vs NCT Monitors

| Aspect | NCT Monitor | NACT Monitor |
|--------|-------------|--------------|
| Perspective | Protocol compliance | Adversarial capability |
| `require` semantics | "Protocol MUST do this" | "Attacker CAN do this if..." |
| State tracking | Connection / stream state | Attack progress, footholds |
| `_finalize` checks | Data transferred, no errors | Attack objectives achieved |

### NACT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Threat model defined | A threat model grounds the test in realistic attack scenarios. |
| Attack entities created | Every attack needs attacker, target, and optionally bot / C2 / MIM entities in `apt_entities/`. |
| Adversarial monitors written | NACT requires adversarial monitors — NCT monitors enforce compliance, not attacks. |
| All 6 APT stages considered | All stages apply. Some may be trivial, but each must be explicitly addressed. |
| Persistence modeled | Include persistence for a complete and realistic attack model. |

### Common NACT Mistakes

- Missing attack entity definitions — define entities in `apt_entities/` with attack-specific state.
- Confusing NCT and NACT monitors — NACT models what the attacker CAN do, not compliance.
- Skipping threat model — complete threat modeling before spec work.

---

## NSCT

Simulation-based testing via Shadow Network Simulator. Reuses NCT Ivy specs; difference is `type: shadow_ns` in PANTHER config. Requires `build_mode: ""` (Shadow-compatible).

For topology config examples, NCT vs NSCT comparison, and seed / replay semantics, Read `references/comprehensive-methodology-detail.md`.

### NSCT Checkpoints

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Topology design complete | Phase 2 must produce a validated node / link topology before any config writing. |
| Simulation config defined | Proper topology ensures the simulation tests what you intend. |
| Correct build mode selected | Shadow requires `build_mode: ""` — other modes are for NCT / NACT Docker environments. |
| Deterministic seed configured | Reproducibility is Shadow's key advantage. Always set and document seeds. |
| Network conditions modeled | Latency / loss / bandwidth modeling is the reason to use Shadow over Docker. |
| Configuration validated | Run `panther config validate --config <file>` before execution. |

### Common NSCT Mistakes

- **Wrong build mode** — use empty string `""` for Shadow NS compatibility; other modes are for NCT / NACT Docker environments.
- **Missing seed configuration** — tests run with random seeds, losing reproducibility. Always configure `seed` in the experiment YAML for Shadow runs.
- **Skipping topology design** — complete Phase 2 topology design before writing config.
- **Using NCT Docker environment by accident** — verify `network_environment.type` is `shadow_ns`, not `docker_compose`.

---

## RFC-to-Ivy Mapping

For RFC 2119 normative-language semantics (MUST / MUST NOT / SHOULD / MAY), concrete `require` / `before` / `after` mapping patterns with examples for transport-parameter validation, state-transition guards, counting / ordering assertions, and the Ivy-construct reference table, Read `references/rfc-to-ivy-mapping.md`.

---

## Verification Workflow

Load `references/comprehensive-methodology-detail.md` for failure patterns, debugging cycle, common errors, and verification checkpoints.

---

## Quality Gates

### Quality Dimensions

| Dimension | Weight | Tool Used | What It Checks |
|-----------|--------|-----------|----------------|
| Structural | 25% | `ivy_diagnostics(mode="structural")` | `#lang` header, balanced braces, includes, file structure |
| Type Safety | 30% | `ivy_verify` | Formal verification, invariants, type correctness |
| Semantic | 20% | `ivy_model_info` + checklist | Naming, invariant coverage, guards, initialization |
| Traceability | 25% | `ivy_coverage(mode="matrix")` | Bracket tags, RFC coverage, orphaned / untagged assertions |

### Scoring

- Each dimension scores 0–100.
- **Overall** = structural(25%) + type_safety(30%) + semantic(20%) + traceability(25%).
- **PASS**: overall ≥ 70 AND no dimension at 0.
- **FAIL**: overall < 70 OR any dimension at 0.

### Gate Tools

| Gate | Tool | Pass Condition |
|------|------|----------------|
| Structural (25%) | `ivy_diagnostics(mode="structural")` | 0 errors; -20 / error, -5 / warning |
| Type Safety (30%) | `ivy_verify` | Verification succeeds (binary) |
| Semantic (20%) | `ivy_model_info` + `ivy_quality(mode="suggestions")` | Naming, guards, init blocks, no anti-patterns |
| Traceability (25%) | `ivy_coverage(mode="matrix")` + `ivy_coverage(mode="stats")` | All MUST assertions tagged `[rfcNNNN:X.Y]` |
