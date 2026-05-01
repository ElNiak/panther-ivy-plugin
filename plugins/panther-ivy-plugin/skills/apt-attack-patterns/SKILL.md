---
name: apt-attack-patterns
description: "Use when modeling the NACT 6-stage attack lifecycle, attacker entities, or around-block monitors. Authors or extends attack specifications under `protocol-testing/apt/`."
user-invocable: false
context: fork
---

# APT Attack Patterns

**Type:** flexible — adapt principles to context.

**Journal:** read-only knowledge skill. Per `.claude/rules/journaling-contract.md` §1, this skill does NOT write to `.panther-ivy/workflow-journal.yaml`; the orchestrator and the 5 ops-skills are the writer surfaces.

NACT (Network-Attack Compositional Testing) extends NCT with attacker perspective. The APT workspace at `protocol-testing/apt/` mirrors the 14-layer NCT template and adds four attack-specific layers (entities, entity behavior, lifecycle, attack-aware application protocols). This skill catalogues the reusable structural patterns across those layers; the canonical methodology overview lives in the `methodology` skill (auto-loaded on `.ivy` files via its `paths:` frontmatter) and mirrored in the project auto-memory at `~/.claude/projects/<project>/memory/reference_nct_methodology.md`.

## When this applies

You are editing a file under `protocol-testing/apt/` (any of `apt_entities/`, `apt_entities_behavior/`, `apt_lifecycle/`, `apt_protocols/`, `apt_shims/`, `apt_stack/`, or `apt_tests/`), or you are scaffolding a new attack-stage file, malicious-variant packet, or protocol binding.

## References

- `references/attack-stage-examples.md` — verbatim excerpts from three stage files (reconnaissance, c2_communication, exfiltration), the canonical 6-stage lifecycle table, the four extra APT layers, and the NACT-vs-NCT operational divergences (generator bias, role inversion, verification scope).
- `references/apt-protocol-binding.md` — step-by-step template for adding a new protocol under `apt_lifecycle/{prot}_apt_lifecycle/`, plus the per-protocol binding aggregator pattern, around-block attack monitors, attack-entity parameter conventions, and application-layer attack bindings under `apt_protocols/`.

## Integration

- **LOADED BY:** scaffold workflow (Phase 3 Write when the target file path contains `protocol-testing/apt/`); verify workflow (Phase 6 Diagnose when a failure traces to attack-entity or lifecycle logic).
- **LOADS:** the reference files above for concrete code excerpts and the protocol-binding template.

**Related skills:**
- **`specification-patterns`** — the base 14-layer template; APT extends it.
- **`methodology`** — NCT / NACT / NSCT selection and methodology-level guidance.
- **`ivy-syntax`** — Ivy syntax for `around` blocks, `parameter` declarations, and include directives.
- **`ivy-toolkit`** — tool invocations, especially `ivy_analysis(mode="includes")` for tracing APT include closure.
