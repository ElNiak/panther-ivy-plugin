---
name: nact-methodology
description: "Use when working with NACT (Network-Attack Compositional Testing), security testing, APT lifecycle modeling, or attack entity configuration. Covers APT 6-stage lifecycle, attack entities, protocol-specific bindings."
---

<HARD-GATE>
Do NOT write any attack specification code or scaffold attack entities until you have
completed Phase 1 (Explore) and Phase 2 (Plan) via the ivy-workflow-orchestrator skill.
</HARD-GATE>

## Iron Laws
1. NO ATTACK SPEC WRITING without completed threat model
2. NO COMPILATION without passing verification
3. ALWAYS chain to ivy-workflow-orchestrator for spec creation/modification
4. ALWAYS use ivy-toolkit for tool operations (never direct CLI)

## NACT -- Network-Attack Compositional Testing

### Overview

NACT extends NCT to model and test protocols from an attacker's perspective. It uses the APT (Advanced Persistent Threat) lifecycle model to systematically test security properties of protocol implementations. Attack specifications use the same Ivy formal language and before/after monitor pattern as NCT but focus on adversarial behavior.

**Recommended testing order:** NCT first (compliance) -> NACT second (security) -> NSCT third (scale/conditions).

### APT 6-Stage Lifecycle

The attack lifecycle is organized into 3 phases with 6 stages plus a cross-cutting concern:

| Phase | Stage | File |
|---|---|---|
| Infiltration | 1. Reconnaissance | `attack_reconnaissance.ivy` |
| Infiltration | 2. Infiltration | `attack_infiltration.ivy` |
| Infiltration | 3. C2 Communication | `attack_c2_communication.ivy` |
| Expansion | 4. Privilege Escalation | `attack_privilege_escalation.ivy` |
| Expansion | 5. Persistence | `attack_maintain_persistence.ivy` |
| Extraction | 6. Exfiltration | `attack_exfiltration.ivy` |
| Cross-cutting | White Noise | `attack_white_noise.ivy` |

> For full stage descriptions, code examples, directory structure, and the 9-step NACT workflow, see `references/apt-lifecycle-detail.md`.

### Attack Entities

NACT defines additional entity roles beyond NCT's client/server: **Attacker**, **Bot**, **C2 Server**, **Target**, **MIM** (Man-in-the-Middle).

Entity definitions reside in `apt_entities/` with behavioral constraints in `apt_entities_behavior/`. Protocol-specific bindings map generic attack stages to concrete protocol actions in `{prot}_apt_lifecycle/`.

> For entity creation patterns, behavioral constraint examples, and protocol binding details, see `references/attack-entity-patterns.md`.

### Phase Specializations (NACT vs NCT)

NACT follows the same ivy-workflow-orchestrator phases as NCT, with these specializations:

**Phase 1 (Explore):** Same as NCT -- navigate existing models, understand protocol structure.

**Phase 2 (Plan):** APT lifecycle threat modeling REPLACES RFC requirement extraction. Instead of extracting MUST/SHOULD/MAY from RFCs, you:
- Identify which APT stages apply to the target protocol
- Define the threat model (attacker capabilities, attack surfaces)
- Map APT stages to protocol-specific attack actions

**Phase 3 (Execute):** Attack entity creation works ALONGSIDE standard spec writing:
- Create attack entities in `apt_entities/` (Attacker, Bot, C2, Target, MIM)
- Write adversarial monitors in `apt_entities_behavior/` (what attacker CAN do, not what protocol SHOULD do)
- Create protocol-specific bindings in `{prot}_apt_lifecycle/`
- Write attack test specifications in `apt_tests/`

### Relationship to NCT
- **NCT** verifies specification compliance (correct behavior)
- **NACT** verifies security properties (resilience to attacks)
- Both use the same Ivy formal language and before/after monitor pattern
- NACT adds attack entity roles and the APT lifecycle framework
- A comprehensive testing campaign uses both NCT and NACT

### Key Difference: NCT vs NACT Monitors

| Aspect | NCT Monitor | NACT Monitor |
|--------|-------------|--------------|
| Perspective | Protocol compliance | Adversarial capability |
| `require` semantics | "Protocol MUST do this" | "Attacker CAN do this if..." |
| State tracking | Connection/stream state | Attack progress, footholds |
| `_finalize` checks | Data transferred, no errors | Attack objectives achieved |

### Checkpoints -- Verify Before Continuing

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Threat model defined | A threat model grounds the test in realistic attack scenarios. |
| Attack entities created | Every attack needs attacker, target, and optionally bot/C2/MIM entities in `apt_entities/`. |
| Adversarial monitors written | NACT requires adversarial monitors -- NCT monitors enforce compliance, not attacks. |
| All 6 APT stages considered | All stages apply. Some may be trivial, but each must be explicitly addressed. |
| Persistence modeled | Include persistence for a complete and realistic attack model. |

### Common Mistakes

**Missing attack entity definitions**
- **Problem:** Attack spec uses generic entities instead of defining attacker-specific ones
- **Fix:** Define entities in `apt_entities/` with attack-specific state and capabilities

**Confusing NCT and NACT monitors**
- **Problem:** Using `require` (compliance check) instead of attack-specific constraints
- **Fix:** NACT monitors model what the attacker CAN do, not what the protocol SHOULD do

**Skipping threat model**
- **Problem:** Writing attack specs without first identifying applicable APT stages
- **Fix:** Complete Phase 2 threat modeling before any spec work (enforced by hard gate above)

## Integration
- **CHAINS TO:** ivy-workflow-orchestrator (for deep mode -- attack spec creation)
- **LOADS:** ivy-toolkit (for all tool operations)
- **PREREQUISITE:** nct-methodology (NACT extends NCT with attack testing)
- **DISPATCHES:** spec-analyst (Phase 1), traceability-agent (Phase 2), methodology-guide (Phase 3)
- **FAST MODE:** For concept questions about NACT/APT, use this skill directly
- **DEEP MODE:** For attack spec work, invoke ivy-workflow-orchestrator

## Reference Files
- **references/apt-lifecycle-detail.md** -- Full APT 6-stage lifecycle with code examples
- **references/attack-entity-patterns.md** -- Attack entity patterns and protocol bindings
