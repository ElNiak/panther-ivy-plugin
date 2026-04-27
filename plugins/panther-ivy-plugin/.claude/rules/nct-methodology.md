---
paths: ["**/*.ivy", "**/*.spec"]
---

# Canonical 14-layer methodology table

The 14-layer NCT/NACT/NSCT methodology table lives in user auto-memory:

    ~/.claude/projects/<project>/memory/reference_nct_methodology.md

It holds the authoritative 14-layer template (Types / Application / Security / Frame / Packet / Protection / Connection / Transport Params / Error / Entity Defs / Entity Behavior / Shims / Serialization / Utilities), the optional-layer catalog, and the template-selection decision matrix. This file is maintained out-of-band by the graduation-sweep process; do not edit under `.claude/rules/`.

The comprehensive NCT 10-step workflow, NACT 6-stage attack lifecycle, and NSCT simulation workflow live in the plugin for every install at `skills/methodology-reference/references/comprehensive-methodology-detail.md`; the `methodology-reference` skill loads it on demand during build and review workflows. Use the Skill tool rather than hardcoding paths into other skills' references.
