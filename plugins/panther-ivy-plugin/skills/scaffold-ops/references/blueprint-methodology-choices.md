# Scaffold Workflow — Blueprint Methodology Choices

Detailed per-methodology layer selection for Phase 2 Step 3 of the scaffold workflow. This reference documents which layers each methodology requires, what choices the user makes, and how those choices land in `scaffold-state.yaml.layers`.

---

## NCT — Network-Centric Compositional Testing

Use the 14-layer template from the `specification-patterns` skill. Propose which layers apply to the target protocol and aspect:

- Which of the 14 layers are needed for the target protocol.
- Dependency order for construction (Types → Frame → Packet → Connection → …).
- Minimum viable set: typically 7 layers (Types, Frame, Packet, Connection, Entity Defs, Entity Behavior, Shims).
- Which layers already exist and can be reused.

Record the chosen layers in `scaffold-state.yaml.layers` with `status: pending`; Phase 3 updates each to `complete` as it compiles.

## NACT — Network-Attack Compositional Testing

Start from the NCT 7-layer minimum (always included as a prefix), then present a multi-select `AskUserQuestion` for the NACT additions documented in `comprehensive-methodology-detail.md`'s NACT section (the canonical list of APT lifecycle files, attack entities, and cross-cutting patterns).

**Multi-select options** (at least 1 required; the prefix 7 NCT layers are assumed):

1. **Full APT lifecycle** — the 6 attack-lifecycle stages from `attack_reconnaissance.ivy` through `attack_exfiltration.ivy`, composed via `attack_life_cycle.ivy`. Includes: reconnaissance, infiltration, C2 communication, privilege escalation, persistence, exfiltration.
2. **Cross-cutting white_noise** — `attack_white_noise.ivy` for distraction attacks that cover the primary attack operation. Independent of the 6-stage lifecycle; can be included alone or alongside it.
3. **Attack entities package** — entity definitions under `apt_entities/` for the additional roles NACT requires (Attacker, Bot, C2 Server, Target, MIM), plus behavioral constraints under `apt_entities_behavior/`.

Record the chosen subset in `scaffold-state.yaml.layers`; each element keeps `status: pending` until Phase 3 writes it.

## NSCT — Network-Simulator Centric Compositional Testing

Use the NCT 7-layer minimum verbatim — NSCT does not require new `.ivy` files relative to NCT.

**Inform the user**: "NSCT adds a Shadow-NS experiment-config YAML at Phase 6 Wrap-up; the `.ivy` blueprint is identical to NCT."

The NSCT-specific artifact is emitted by Phase 6 Step 1b, not by Phase 2. See `methodology` skill's `references/nsct-experiment-template.md` for the template and the emission substituter.

## Methodology drift note

If `methodology`'s canonical lists change (new NACT lifecycle file, renamed attack entity), update this reference together with `comprehensive-methodology-detail.md` so the multi-select options stay consistent with the canonical methodology text.
