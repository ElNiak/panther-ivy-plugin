---
name: methodology
description: "Use when choosing a testing methodology, starting model construction, or mapping RFC requirements to an Ivy testing strategy. Provides NCT (compliance) / NACT (security) / NSCT (simulation) selection and workflow guidance."
user-invocable: false
paths:
  - "**/*.ivy"
  - "**/skills/*/SKILL.md"
---

# Formal Testing Methodologies

**Type:** flexible — adapt principles to context.

**Journal:** read-only knowledge skill. Per `.claude/rules/journaling-contract.md` §1, this skill does NOT write to `.panther-ivy/workflow-journal.yaml`; the orchestrator and the 6 ops-skills (scaffold-ops / refine-ops / experiment-ops / review-ops / triage-ops / meta-self-mod-ops) are the writer surfaces.

PANTHER's three Ivy testing methodologies are NCT (compliance), NACT (adversarial security), and NSCT (Shadow-NS simulation). All three share the 14-layer specification template (canonical location: this skill body, mirrored in user auto-memory at `~/.claude/projects/<project>/memory/reference_nct_methodology.md`), the before/after monitor pattern, `require` / `export` / `_finalize` semantics, and role inversion. Decision tree: testing RFC compliance → NCT; testing security against attacks → NACT; testing under controlled network conditions → NSCT; unsure → start with NCT (the foundation for both NACT and NSCT). For tool usage across all methodologies, see `ivy-toolkit`.

## Dispatch decision table

Once the methodology is chosen, this table maps the user's situation to the first skill and workflow to load.

| Situation | Methodology | First skill to load | First workflow |
|---|---|---|---|
| RFC compliance test, IUT exists | NCT | `specification-patterns` | `scaffold` |
| Attack / security test, attacker model needed | NACT | `apt-attack-patterns` | `scaffold` |
| Network-condition / replay tests (Shadow simulator) | NSCT | `methodology` (this file) | `scaffold` |
| Existing spec, want to verify | (any) | `verification-failures` | `verify` |
| Existing spec, want coverage / quality verdict | (any) | `verification-failures` | `review` |
| Tools timing out / MCP errors | (any) | (none — direct invocation) | `triage` |

## References

- `references/comprehensive-methodology-detail.md` — full reference: 10-step NCT workflow, NACT attack composition, NSCT simulation, APT 6-stage table, the per-methodology directory structures, NCT/NACT/NSCT checkpoint tables, common-mistake lists, NACT-vs-NCT monitor table, the 14-layer template/optional layers/decision matrix, and the quality-gates scoring system (Structural/Type Safety/Semantic/Traceability dimensions, weights, PASS/FAIL thresholds, gate-tool mapping).
- `references/glossary.md` — calibrated meanings of NCT / NACT / NSCT / isolate / monitor / `_finalize` / role inversion / `export` / `import`.
- `references/walkthrough-nct-quic-server.md` — end-to-end NCT walkthrough on a QUIC server IUT (workspace setup, methodology detection, layer scaffolding, role inversion, G3 / G4 / G5 gates, build ↔ verify hand-off via `pending_dispatch`).
- `references/rfc-to-ivy-mapping.md` — RFC 2119 normative-language semantics (MUST / MUST NOT / SHOULD / MAY) with concrete `require` / `before` / `after` mapping patterns and the Ivy-construct reference table.
- `references/nsct-experiment-template.md` — the NSCT Shadow-NS experiment-config template consumed by `build` Phase 6 Step 1b (placeholders, target path, substitution rules).

For the concrete pattern library backing NACT (APT 6-stage lifecycle, stage-file scaffolding, attack-entity composition, protocol-binding template, `around`-block monitors), load the `apt-attack-patterns` skill via the `Skill` tool. For the full error-to-fix lookup table, load `verification-failures`.
