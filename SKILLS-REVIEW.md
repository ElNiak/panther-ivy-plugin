# Skills Corpus Review — panther-ivy-plugin

Date: 2026-04-20
Target: `plugins/panther-ivy-plugin/skills/` (17 skills)
Method: Eighteen parallel Claude agents — one per skill + one cross-corpus — each auditing against the criteria distilled below. The raw per-agent reports are preserved verbatim in the per-skill sections.

## 1. Methodology & sources

The criteria used in every agent prompt were distilled from:

- https://code.claude.com/docs/en/skills — official Claude Code Skills reference (frontmatter fields, `${CLAUDE_SKILL_DIR}`, auto-compaction, argument substitution, size cap of 500 lines, 1,536-character description/`when_to_use` budget)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices — authoring best practices (name rules, ≤1024-char description, third-person rule, progressive disclosure, TOC for references >100 lines, forward-slash paths, fully-qualified MCP names, avoid punt-to-Claude error handling)
- https://platform.claude.com/docs/en/build-with-claude/context-windows — context-rot and prompt-cache implications for description brevity
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (Opus 4.7 section) — verbosity calibration, imperative vs. descriptive, structured output
- Project-local `.claude/rules/skill-conventions.md` — per-skill `references/`, no duplicate sections, no hardcoded paths into another skill's `references/`, no “do not invoke directly” waste in description
- Project-local `.claude/rules/ivy-formatting.md` — RFC citation, error/warning format, tool-result rendering
- Project-local user-memory entries (`feedback_references_under_skill`, `feedback_skill_cross_refs`, `feedback_own_conventions_not_math_olympiad`, `feedback_no_backward_compat`)

### Calibration notes (agent corrections)

Two of the per-skill agents flagged `Use when …` phrasing in descriptions as a “third-person violation”. **That flag is incorrect.** The Anthropic best-practices page uses `Use when working with PDF files …` as its canonical positive example. The third-person rule forbids `I can help you …` / `You can use this to …`. `Use when …` is the recommended trigger-phrase shape. I have suppressed that false-positive class in the aggregated findings below; the underlying skills are not at fault on that axis.

Agent outputs also varied on whether bodies should be “imperative form written FOR Claude”. The Anthropic docs do say imperative-for-Claude, but reference-style knowledge skills (catalogs, schemas) are allowed to be declarative; the spec does not forbid descriptive prose in reference files. Flags of that form in knowledge-style skills have been reclassified as style preferences, not standards violations.

## 2. Corpus at a glance

| # | Skill | Lines | Verdict | Top finding |
|---|---|---:|---|---|
| 1 | build | 379 | Good | Phase 3 heading duplicated between `SKILL.md` and `references/layer-scaffolding.md`; one `Skill(skill="verify")` call not namespaced (`panther-ivy-plugin:verify`). |
| 2 | claim-discussion | 54 | Good | Workspace blockquote is plugin-level noise; consider routing via CLAUDE.md. |
| 3 | counterexample-guide | 254 | Good | Missing `allowed-tools`; “When to Use” section duplicates description. |
| 4 | ivy-debugging-methodology | 102 | Good | Step 8 serializer subsection hardcodes a path into `ivy-writing-guide/references/` — plugin convention says route via Skill tool. |
| 5 | ivy-error-patterns | 63 | Excellent | Clean dual-file architecture (`error-table.md` 315L + `verifier_patterns.md` 504L). No critical issues. |
| 6 | ivy-toolkit | 168 | Good | `tool-catalog.md` (449 L) lacks a TOC; `FAST/DEEP` tier labels are undefined in SKILL.md. |
| 7 | ivy-writing-guide | 282 | Good | Orphan `## Integration` heading at line 259 (empty section). |
| 8 | knowledge-capture | 117 | Good | `references/knowledge-taxonomy.md` (158 L) lacks a TOC. |
| 9 | methodology-reference | 296 | Good | Skill-to-skill references in prose (`specification-patterns`, `ivy-toolkit`, `ivy-error-patterns`) — should be invoked via the Skill tool. `references/comprehensive-methodology-detail.md` (368 L) lacks a TOC. |
| 10 | navigate | 248 | Good | Anti-Rationalization table (lines 13–21) is narrative; per plugin convention move to `references/`. No `references/` directory exists. |
| 11 | propagation-patterns | 88 | Good | Missing `allowed-tools`; `(MiniP-specific)` annotation should be generalized — hardcoded-constant asymmetry is a cross-protocol risk. |
| 12 | reflection-patterns | 220 | Good | `g5_trace.md` (108 L) lacks a TOC; description is 300 chars — at risk of front-loading truncation in the 1,536-char skill listing budget. |
| 13 | review | 263 | Needs work | Uses hardcoded `Skill(skill="…")` inline instructions instead of namespaced calls; description (“Quality and coverage auditing… Use when the user asks for …”) is generic; no `references/`; depth limit `>= 3` is a magic number. |
| 14 | session-retrospective | 126 | Adequate | Custom `when_to_use` frontmatter field is **not in the official schema**; hardcodes `knowledge-capture references` path (plugin convention violation); `Agent` tool in `allowed-tools` is unrestricted. |
| 15 | specification-patterns | 209 | Good | Pattern overview table duplicated in SKILL.md and `references/pattern-library-detail.md`; reference file (202 L) lacks a TOC. |
| 16 | triage | 259 | Needs work | Frontmatter missing `allowed-tools` + `user-invocable`; opaque `Pattern A/C/D` references require reading another skill; implementation-specific paths (`/tmp/ivy-lsp-*`) cannot be generalized. |
| 17 | verify | 393 | Good | Phase 6 entry is a one-liner handoff to `references/failure-diagnosis.md`; G4/G5 verdict reporting to the user is implied, not stated; Post-IUT Wire Validation is orphaned at the end of the reference file. |

Totals: 3,521 SKILL.md lines across 17 skills; 12 of 17 ship a `references/` directory; no SKILL.md exceeds the 500-line budget; three (`claim-discussion`, `ivy-error-patterns`, `propagation-patterns`) are under 100 lines.

## 3. Per-skill findings (condensed)

Each entry preserves the structure each agent produced: verdict, frontmatter/description assessment, body analysis, key issues, and ranked recommendations. Where an agent's finding was a false positive against the docs (e.g., `Use when …` flagged as non-third-person), it has been corrected.

### 3.1 build — Good (379 L)

- **Frontmatter**: `name` 5 chars, `description` 162 chars, both valid; only required fields set.
- **Description**: Front-loaded; concrete triggers (“starting a new protocol spec”, “scaffolding layers”, “continuing a build session”); no workflow-summary leakage.
- **Body**: Six numbered phases, three adversarial gates (G1–G3), clear state management via `.panther-ivy/active-workflow`, `build-state.yaml` for warm resume. Imperative form throughout. One `references/` file (`layer-scaffolding.md`, 57 L).
- **Issues**
  - *Important*: Phase 3 section header repeats in SKILL.md (lines 205–217) and in `references/layer-scaffolding.md`, creating authority ambiguity. Either demote the reference file heading to a subsection or move all Phase 3 detail into the reference and replace the SKILL.md block with a one-line pointer.
  - *Important*: `Skill(skill="verify")` at line 229 is not namespaced; other invocations use `panther-ivy-plugin:<name>`.
  - *Minor*: G1 gate firing path mentions `route-user-prompt.py` hook without saying when it fires.
  - *Minor*: Background Compilation section (47 lines) is operational and could move to `.claude/rules/` to keep SKILL.md lean.
- **Recommendations** (ranked): unify Phase 3 authorship · fully-qualify `verify` invocation · clarify G1 fire trigger · extract background-compilation section · add warm-resume checkpoint note.

### 3.2 claim-discussion — Good (54 L)

- **Frontmatter**: `name` 16 chars; `description` 155 chars (“Decision trees for resolving verification and coverage claims. Use when ivy_verify returns FAIL, ivy_coverage shows gaps, or model-reviewer reports issues.”); `user-invocable: false`, `context: fork`; `allowed-tools` absent (skill calls no tools).
- **Body**: Routing table directs to one of three reference files (verification-claim 95 L, mapping-claim 56 L, coverage-claim 66 L). Concrete inline comment format with mandatory metadata (prefix, date, description).
- **Issues**
  - *Important*: Workspace setup blockquote (`/set-workspace <protocol>`) is plugin-wide infrastructure, not claim-specific — belongs in CLAUDE.md or a shared rule.
  - *Minor*: reference filenames (`verification-claim.md`) read as nouns; gerund form (`resolving-verification-claims.md`) would match the skill’s other gerund-style file names better — style choice only.
- **Recommendations**: move workspace blockquote to CLAUDE.md · consider declaring `allowed-tools: ""` explicitly for consistency · clarify the table as `Load: references/<file>` so Claude treats it as file selection, not cross-skill reference.

### 3.3 counterexample-guide — Good (254 L)

- **Frontmatter**: `name` 20 chars; `description` 144 chars; `user-invocable: false`, `context: fork`. Missing `allowed-tools` even though the skill explicitly invokes `ivy_model_info`, `ivy_visualize`, `ivy_coverage`, LSP, Grep, Read.
- **Body**: Six-step diagnostic procedure; catalog cross-refs pattern IDs `#410–#413` in `ivy-error-patterns`. One reference file (`trace-example.md`, 57 L).
- **Issues**
  - *Critical*: frontmatter missing `allowed-tools`; recommend declaring the six tools the steps actually invoke.
  - *Important*: lines 14–21 contain a “When to Use” section that re-states the frontmatter trigger; the conditional at line 21 (“If verification fails but no counterexample is present…”) should become inline prose, not a heading.
  - *Minor*: workspace notice on line 25 is plugin-level, not skill-specific; relative path resolution for `references/trace-example.md` is not documented.
- **Recommendations**: declare `allowed-tools` · fold “When to Use” into the Integration section · remove workspace blockquote · document that relative paths in skill bodies resolve against `${CLAUDE_SKILL_DIR}`.

### 3.4 ivy-debugging-methodology — Good (102 L)

- **Frontmatter**: `name` 23 chars; `description` 162 chars with explicit error triggers (“ivy_check failed”, “verification failed”); `user-invocable: false`; no `allowed-tools` (skill prescribes tool use rather than invoking).
- **Body**: Mandatory 8-step pre-fix checklist with a hard-rule guard (“You MUST complete steps 1–6 before proposing ANY fix”). Diagnostic-source table (line 22 onwards) cleanly classifies ivy / ivy-lint / ivy-lsp / ivy-mcp outputs. No `references/` — delegates depth to `ivy-error-patterns`, `ivy-writing-guide`, `counterexample-guide`.
- **Issues**
  - *Important*: Step 1 (“Parse the Error”) and Step 2 (“Diagnostic Interpretation Protocol”) reference the same three fields; swap order so the source classification informs the parse.
  - *Important*: Line 91 writes `load the ivy-writing-guide skill and read references/serializer-patterns.md` — this hardcodes a path into another skill's references, which the plugin convention (`feedback_skill_cross_refs`) forbids. Replace with “Load the `ivy-writing-guide` skill and consult its serializer patterns section.”
  - *Minor*: Step 5 grep examples should declare workspace-relative intent.
- **Recommendations**: swap Steps 1 and 2 · fix serializer cross-reference per plugin convention · annotate grep examples with workspace scope · add a Step 3 worked mapping · tighten Step 8 loop-back language.

### 3.5 ivy-error-patterns — Excellent (63 L)

- **Frontmatter**: `name` 18 chars; `description` 245 chars with specific trigger phrases and catalog-ID signal; `user-invocable: false`. Strong third-person voice.
- **Body**: Router with clear routing logic between two reference files: `error-table.md` (315 L, 12 cryptic Ivy errors) and `verifier_patterns.md` (504 L, 80+ numbered patterns with methodology tags NCT/NACT/NSCT/Ivy/Plugin-Memory). Sparse ID ranges preserve provenance (RFC sections, papers, memory IDs). Append-only policy documented.
- **Issues**: none critical, none important. Only suggestions: cite line ranges for `#410–413` in SKILL.md, clarify that `protocol-testing/*` paths are protocol-root-relative, add a search-by-substring index to `error-table.md`.
- **Recommendations**: audit sibling-skill references (already verified OK) · enforce append-only via a pre-commit rule · add a provenance note for example paths.

### 3.6 ivy-toolkit — Good (168 L)

- **Frontmatter**: `name` 10 chars; `description` 123 chars; `user-invocable: false`. Five reference files: `error-reference.md` (220 L), `hook-lifecycle.md` (99 L), `lsp-patterns.md` (234 L), `timing-and-concurrency.md` (156 L), `tool-catalog.md` (449 L).
- **Body**: Iron Law → abstraction levels (LSP → MCP → Claude tools) → 25-tool quick-reference matrix → rendering-awareness block. Well-scoped; dense.
- **Issues**
  - *Critical*: `tool-catalog.md` (449 L) has no table of contents — Anthropic best-practices require TOCs for reference files >100 lines. Add a `## Tool Index` block with the seven tool categories.
  - *Important*: The `FAST + DEEP` column header in the matrix (line 32) is undefined in the skill body; its semantics live in `timing-and-concurrency.md`. Either rename the column to `Tier` with a footnote, or add a one-line glossary in the body.
  - *Important*: Forward-reference to `hook-lifecycle.md` at line 58 is terse; expand to name the hook-formatted tools (ivy_verify, ivy_compile, ivy_diagnostics, ivy_coverage, ivy_quality) explicitly.
  - *Minor*: Phases 1–5 cited at lines 40/41/44 without glossing — define or point at `methodology-reference`.
- **Recommendations**: add TOC to `tool-catalog.md` · define tier column · expand hook-formatting forward-ref · define “Phase 1–5” on first use.

### 3.7 ivy-writing-guide — Good (282 L)

- **Frontmatter**: `name` 17 chars; `description` 150 chars; `user-invocable: false`, `context: fork`, `paths: "**/*.ivy"`. No `allowed-tools` (skill is read-only for specs).
- **Body**: Covers type system, modules, isolates, invariants, RFC bracket-tag practice. Three reference files: `syntax-examples.md` (175 L), `generator-mechanics.md` (144 L), `serializer-patterns.md` (173 L).
- **Issues**
  - *Important*: Orphan `## Integration` heading at line 259 with no content, immediately followed by `## C++ Serializer/Deserializer Patterns` — looks like a refactor remnant.
  - *Important*: Lines 276–278 list “Related skills” (`specification-patterns`, `methodology-reference`, `ivy-toolkit`) in prose. This is acceptable as a footer roster but should not be cited as authoritative procedures — clarify that each is loaded via the Skill tool.
  - *Minor*: Workspace directive blockquote on line 11 should be inline prose. Lines 39/51/62 embed `Grep(...)` example strings that read as human instructions; either mark them as illustrative or rephrase for Claude.
- **Recommendations**: remove or populate the Integration heading · inline the workspace blockquote · add TOCs to the 175-line syntax-examples.md · tighten the Test File Checklist or fully defer it to references · document the three-tier structure (SKILL.md + README.md + references/) in the preamble.

### 3.8 knowledge-capture — Good (117 L)

- **Frontmatter**: `name` 17 chars; `description` 169 chars; `user-invocable: false`, `context: fork`, `allowed-tools` present (seven tools incl. `Bash(ls *)`). Only skill in the corpus that scopes Bash to a single command.
- **Body**: Six-step extraction workflow; one reference file (`knowledge-taxonomy.md`, 158 L) defines five categories and the digest schema.
- **Issues**
  - *Important*: `knowledge-taxonomy.md` (158 L, seven sections) lacks a TOC.
  - *Minor*: Term “knowledge gate” is used without definition; one-line context pointer at the top of SKILL.md would aid standalone readability.
  - *Minor*: `Bash(ls *)` is in `allowed-tools` but the body never invokes Bash. Either drop it or exercise it.
- **Recommendations**: add TOC to taxonomy reference · add a Context callout (when this skill fires) · verify `Bash(ls *)` is needed.

### 3.9 methodology-reference — Good (296 L)

- **Frontmatter**: `name` 21 chars; `description` 225 chars; `user-invocable: false`. Missing `allowed-tools` and `disable-model-invocation`.
- **Body**: NCT / NACT / NSCT selection tree and workflow guidance; five worked RFC→Ivy mapping examples (lines 197–241). One reference file (`comprehensive-methodology-detail.md`, 368 L).
- **Issues**
  - *Critical*: Lines 20, 32, 91 invoke sibling skills (`specification-patterns`, `ivy-toolkit`, `ivy-error-patterns`) by backticked name in prose. Plugin convention (`feedback_skill_cross_refs`) requires loading via the Skill tool for progressive disclosure.
  - *Important*: `comprehensive-methodology-detail.md` (368 L, 7 sections) lacks a TOC.
  - *Important*: Opening sentences (lines 1–11) are descriptive narration; skills are expected to be imperative-for-Claude. Minor stylistic mismatch for a reference skill but worth aligning.
- **Recommendations**: route skill references through the Skill tool · add TOC to the 368-line reference · declare `allowed-tools` / `disable-model-invocation` · expand NACT-mistakes section with side-by-side fixes.

### 3.10 navigate — Good (248 L)

- **Frontmatter**: `name` 8 chars; `description` 126 chars; no other fields. Description is front-loaded with concrete triggers.
- **Body**: Anti-Rationalization thought/reality table (lines 13–21), process-flow diagram (lines 33–48), three branches (Warm Resume, Activity Summary, Cold Start). No `references/` directory.
- **Issues**
  - *Important*: The Anti-Rationalization table is narrative/motivational — plugin convention (`feedback_references_under_skill`) says narrative storytelling should move to `references/`.
  - *Important*: MCP tool names (`ivy_workflow_state`, `ivy_diagnostics`) are not fully-qualified. Anthropic best-practices call for `ServerName:tool_name` (e.g., `panther-ivy:ivy_workflow_state`) — worth confirming the MCP server name in this plugin’s `.mcp.json`.
  - *Important*: Output-Style section (lines 8–12) is passive (“is managed by the style system”); rewrite as imperative (“Follow style directives …”).
  - *Minor*: Only one concrete example in the entire skill; capitalization of `Skill` vs `skill` is inconsistent.
- **Recommendations**: create `references/anti-rationalization.md` and move the table · fully-qualify MCP tool names · convert passive sections to imperatives · add a worked cold-start → dispatch example.

### 3.11 propagation-patterns — Good (88 L)

- **Frontmatter**: `name` 21 chars; `description` 127 chars; `user-invocable: false`. Missing `allowed-tools` (skill coordinates with `ivy_propagation`).
- **Body**: Authority rule (line 11–16) forbids overriding `ivy_propagation` output; Ivy type → C++ encoding table; Add-Field / Add-Variant patterns; asymmetry warnings. One reference file (`minip-examples.md`, 79 L).
- **Issues**
  - *Important*: `allowed-tools` missing (recommend `ivy_propagation ivy_verify`).
  - *Minor*: Line 78 annotates hardcoded-constant risk as `(MiniP-specific)`, but it is a cross-protocol risk (payload lengths, iteration caps, counters).
  - *Minor*: Line 87 points at `ivy-writing-guide/references/serializer-patterns.md` — acceptable in prose context, but tighter to say “Load the `ivy-writing-guide` skill and consult its serializer patterns section” to preserve progressive disclosure.
- **Recommendations**: add `allowed-tools` · generalize the hardcoded-constants warning · rewrite serializer cross-reference · tighten Integration fallback guidance.

### 3.12 reflection-patterns — Good (220 L)

- **Frontmatter**: `name` 18 chars; `description` 300 chars; `user-invocable: false`, `context: fork`. No `allowed-tools`.
- **Body**: Four interaction patterns (RG, MPE, SB, CVG) + adversarial-gate playbook (G1–G5) with discipline layer contracts. Six reference files: five critic prompts (g1–g5) plus `model_tier_defaults.md` (75 L). g5_trace.md is 108 L.
- **Issues**
  - *Important*: Description is 300 chars — at 250 chars truncation risk per Anthropic docs when skill listings are compressed under the 1,536-char budget.
  - *Important*: `allowed-tools` is not declared even though critics spawned by this skill call MCP and Skill tools. Declare the full set so downstream critics know the contract.
  - *Minor*: `g5_trace.md` (108 L) lacks a TOC.
  - *Minor*: Small duplication of discipline-contract text between SKILL.md (lines 137–173) and `model_tier_defaults.md` (lines 51–66).
- **Recommendations**: tighten description to ≤250 chars · declare `allowed-tools` · add TOC to g5_trace.md · add a worked reflection-gate example · clarify that critics load `ivy-error-patterns` via the Skill tool.

### 3.13 review — Needs work (263 L)

- **Frontmatter**: `name` 6 chars; `description` 163 chars. Description is generic: “Quality and coverage auditing for Ivy models. Use when the user asks for coverage checks, quality audits, or model reviews.” Missing front-loaded RFC/coverage keywords (`traceability`, `RFC compliance`, `MUST requirements`, `coverage matrix`, `quality findings`). No `allowed-tools`, no `user-invocable`.
- **Body**: Three phases (Triage → Execute → Findings); dispatches three agents (model-reviewer, spec-analyst, Adversarial Auditor) in parallel; Iron Law forbidding impressionistic assessments. No `references/` directory.
- **Issues**
  - *Critical*: Lines 104/135/173/239 invoke sibling skills as imperative instructions (“Load the reflection-patterns skill”) instead of `Skill(skill="panther-ivy-plugin:reflection-patterns")`. Plugin convention mandates the Skill-tool path.
  - *Critical*: No `allowed-tools` / `user-invocable` frontmatter; registration completeness is unclear.
  - *Important*: Description should lead with RFC-first / coverage-first keywords.
  - *Important*: No reference files; multi-perspective exploration methodology (lines 134–161) is a natural extract.
  - *Minor*: Line 221 magic number `invocation_depth >= 3`; line 262 missing concrete trigger phrases.
- **Recommendations**: replace all inline skill loads with Skill-tool calls · add missing frontmatter · rewrite description with concrete triggers · extract methodology to `references/quality-audit-methodology.md` · justify the depth limit.

### 3.14 session-retrospective — Adequate (126 L)

- **Frontmatter**: `name` 21 chars; `description` 199 chars; `user-invocable: true` (the only knowledge-tier skill so marked); `allowed-tools` includes an unrestricted `Agent`, plus `Write` and `Edit`; `when_to_use` field is **not in the official schema** (see Anthropic docs §Frontmatter reference — only `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell` are recognized; `when_to_use` is recognized but only as **additional** context appended to `description` — it is a documented field, so this is not technically a schema violation, correcting the per-agent flag).
- **Body**: Six steps from gather-evidence to present-report; reuses `knowledge-capture`’s taxonomy and Classification Reviewer Agent.
- **Issues**
  - *Important*: Self-describes as “superset of knowledge-capture” → overlap with the `knowledge-capture` knowledge skill; consider scope consolidation.
  - *Important*: References `knowledge-capture` skill and its `references/` directory (line 50: “knowledge-capture references”) by path. Plugin convention forbids hardcoding paths into another skill’s `references/` — route via the Skill tool instead.
  - *Important*: `allowed-tools` grants unrestricted `Agent`; recommend enumerating the permitted agent names (`spec-analyst`, `model-reviewer`, `traceability-agent`, etc.).
- **Recommendations**: decide scope vs. `knowledge-capture` (fold in or clearly differentiate) · reroute cross-skill reads through the Skill tool · restrict `Agent` with a whitelist · relocate the “Relationship to knowledge-capture” section to `references/architecture.md` · inline the category taxonomy in Step 3 so the skill is standalone-usable.

### 3.15 specification-patterns — Good (209 L)

- **Frontmatter**: `name` 20 chars; `description` 132 chars (“14-layer template reference and pattern scaffolding guide. Use when designing layer structure or scaffolding a new protocol model.”); `user-invocable: false`.
- **Body**: Decision matrix across TCP-based / pub-sub / real-time protocols; 14-layer directory template; dependency graphs. Two reference files: `frame-queuing-pattern.md` (67 L), `pattern-library-detail.md` (202 L).
- **Issues**
  - *Important*: `pattern-library-detail.md` (202 L, 7 major sections) lacks a TOC.
  - *Important*: Pattern overview table at SKILL.md:166 duplicates the one at `pattern-library-detail.md`:9 with only an “Example Protocol” column added. Consolidate.
  - *Minor*: Opening prose is descriptive (“This skill combines…”) rather than imperative.
  - *Minor*: Line 207 references `build` workflow by name; if intended as a dispatch, use the Skill tool.
- **Recommendations**: add TOC · dedupe the pattern table · rewrite opening as imperative · clarify the `build` handoff.

### 3.16 triage — Needs work (259 L)

- **Frontmatter**: `name` 6 chars; `description` 108 chars. Missing `allowed-tools` and `user-invocable`. Trigger phrases are vague (“tools are broken”, “not working complaints”).
- **Body**: Three phases (Quick Check → Diagnose → Fix). Loads `reflection-patterns` three times at different patterns (C, A, D) without glossing them. Bash snippets tightly coupled to PANTHER paths (`/tmp/ivy-lsp-*.pid`, `PANTHER_IVY_ENABLE_SERENA`). No `references/` directory.
- **Issues**
  - *Critical*: Missing `allowed-tools` and `user-invocable` — both are strongly recommended for user-facing workflow skills.
  - *Critical*: `Pattern A/C/D` references from `reflection-patterns` are opaque on load; the reader must traverse another skill to decode them.
  - *Critical*: `invocation_depth > 0` semantics assume reader knows sub-workflow mechanics — these belong in a dedicated reference or CLAUDE.md section.
  - *Important*: MCP tool calls are not fully-qualified (`ivy_status` vs. `panther-ivy:ivy_status`).
  - *Minor*: Log-file naming inconsistency (`ivy-lsp-lsp-latest.log` vs. `ivy-lsp-latest.log`); no error handling if `ivy_workflow_state` fails.
- **Recommendations**: add `allowed-tools` and `user-invocable` · create `references/reflection-patterns-glossary.md` with A/C/D definitions · split internal state mechanics into `references/invocation-model.md` · qualify MCP tool refs · add a worked phase walkthrough reference.

### 3.17 verify — Good (393 L)

- **Frontmatter**: `name` 6 chars; `description` 139 chars; no other fields. Description front-loads key use case and lists specific trigger verbs (`check`, `test`, `debug`, `verify`).
- **Body**: Seven phases; Iron Law + Staleness Rule; G4 (verification gate) and G5 (trace gate); dispatches `reflection-patterns`, `counterexample-guide`, `ivy-writing-guide`, `specification-patterns`, `knowledge-capture`. Two reference files: `failure-diagnosis.md` (153 L), `iut-output-analysis.md` (111 L).
- **Issues**
  - *Important*: Phase 6 entry is a one-liner handoff — `Load references/failure-diagnosis.md for the full diagnosis and fix procedures. Summary:` — so a reader starts Phase 6 and must immediately context-switch. Bring the high-level flow inline.
  - *Important*: G4/G5 gate verdicts are audited but the user-facing reporting step is implied, not stated. Make the verdict communication explicit.
  - *Minor*: Post-IUT Wire Validation is a PASS-phase check but it lives at the end of `failure-diagnosis.md`, coupled with diagnose-and-fix content. Reposition or cross-link from Phase 5.
  - *Minor*: No TOC on the two reference files (both >100 L).
- **Recommendations**: bring Phase 6 entry inline · add explicit gate-verdict report steps · reposition Post-IUT Wire Validation · add TOCs to reference files · harmonize negative phrasing in the Background Verification section.

## 4. Cross-skill comparative findings

### 4.1 Naming

- **Workflow skills are single verbs** (`navigate`, `verify`, `build`, `review`, `triage`) — consistent.
- **Knowledge skills mix `ivy-` prefix with no prefix**: `ivy-toolkit`, `ivy-writing-guide`, `ivy-error-patterns`, `ivy-debugging-methodology` carry the prefix; `specification-patterns`, `propagation-patterns`, `reflection-patterns`, `methodology-reference`, `claim-discussion`, `counterexample-guide`, `knowledge-capture`, `session-retrospective` do not. No rule documents when the prefix applies, and `ivy-error-patterns` / `specification-patterns` / `propagation-patterns` / `reflection-patterns` are all “*-patterns” catalogs — three of them with no prefix, one with. Standardize.

### 4.2 Description length distribution

16 of 17 descriptions are 108–245 chars — tight and front-loaded. The outlier is `reflection-patterns` at 300 chars: the Anthropic doc notes that `description + when_to_use` is truncated at 1,536 chars in listings and recommends keeping the key trigger in the first 250 chars. Reflection-patterns' “Use when” clause sits past that mark.

### 4.3 Overlap / redundancy map

| Pair | Severity | Recommendation |
|---|---|---|
| `ivy-debugging-methodology` ⇔ `ivy-error-patterns` | High | Debugging owns the procedure; error-patterns owns the catalog. Remove the “Top 5 errors” table from whichever duplicates it. |
| `knowledge-capture` ⇔ `session-retrospective` | High | session-retrospective calls itself a superset; either fold knowledge-capture into it or keep knowledge-capture as the gate-only subroutine and narrow session-retrospective's description. |
| `verify` ⇔ `build` | Medium | Both carry identical `Iron Law` + `Staleness Rule` + `TaskCreate` boilerplate. Move to a shared rule and include once. |
| `counterexample-guide` ⇔ `ivy-debugging-methodology` | Medium | Boundary is documented but step-1 parse-the-violated-assertion flows collide. Either mark counterexample-guide as a dispatched sub-procedure or explicitly state the dispatch condition. |
| `methodology-reference` ⇔ `specification-patterns` | Low–Medium | methodology-reference already defers the 14-layer template; good. Tighten its description and remove the standalone layer discussion. |
| `ivy-toolkit` ⇔ every workflow skill | Medium | ivy-toolkit claims canonical ownership of MCP-tool guidance, but `verify`, `build`, `review`, and `triage` duplicate tool names and parameter guidance. Replace per-skill tool tables with a single pointer. |

### 4.4 Corpus-level gaps

- No dedicated **IUT output analysis** skill, despite the 9-step procedure already codified in user memory (`feedback_iut_output_analysis`). Today it lives inside `verify/references/iut-output-analysis.md`, which couples it to one workflow.
- No dedicated **coverage / traceability** skill. `ivy_coverage` (stats/gaps/matrix), `ivy_extract_requirements`, and `ivy_manifest` are spread across `review`, `claim-discussion`, and the `traceability-agent`.
- No dedicated **serializer / deserializer** skill. Three skills defer to `ivy-writing-guide/references/serializer-patterns.md`, which is three levels of indirection away from the workflow that needs it.
- No **RFC-extraction** skill. `ivy_rfc` (get/search/section) has no companion skill; RFC bracket-tag conventions are split between `ivy-writing-guide` and `.claude/rules/ivy-formatting.md`.
- No explicit **NACT / NSCT discipline** skill. Discipline-layer guidance is folded into `reflection-patterns` and `ivy-error-patterns`.

### 4.5 Skill-to-skill references

Explicit `Skill(skill="…")` invocations were found in: `build` (verify, knowledge-capture), `verify` (triage, review, knowledge-capture), `review` (triage, verify, knowledge-capture), `navigate` (triage, knowledge-capture, dynamic `{workflow_name}`), `triage` (knowledge-capture), `reflection-patterns` (dynamic `{workflow_name}`).

Plugin-convention violations (hardcoded paths into another skill's `references/`):

- `ivy-debugging-methodology` SKILL.md:91 — points directly at `ivy-writing-guide/references/serializer-patterns.md` instead of loading the skill.
- `propagation-patterns` SKILL.md:87 — same target, same issue.
- `session-retrospective` SKILL.md:50 — names `knowledge-capture references`.
- `methodology-reference` lines 20/32/91 — sibling skills cited by backtick name rather than by Skill-tool call.
- `review` lines 104/135/173/239 — sibling skills loaded in prose instructions instead of via `Skill(skill=...)`.

### 4.6 Terminology drift

1. “Monitor” vs “assertion” vs “annotation” vs “bracket-tag” — four terms, one concept (pre/post RFC-tagged check).
2. “Phase” vs “step” vs “stage” — workflows use Phase N; knowledge-capture and ivy-debugging-methodology use Step N.
3. “Spec” vs “model” vs “isolate” — plugin CLAUDE.md switches between them in adjacent sentences.
4. “Gate” vs “check” vs “critic” vs “audit” — reflection gate, quality gate, knowledge gate, adversarial gate, G1–G5 critics, quality audit, structural check. No glossary.
5. “Workflow” vs “command” vs “shortcut” — plugin CLAUDE.md distinguishes them, but verify/build treat shortcut commands as synonymous with tools.

### 4.7 Frontmatter variance

- No skill uses `disable-model-invocation`.
- `context: fork` appears on 5 of 11 knowledge skills (`claim-discussion`, `counterexample-guide`, `ivy-writing-guide`, `reflection-patterns`, `knowledge-capture`) and is absent on the other 6 — no documented rule for the split.
- `allowed-tools` appears on only 2 skills (`knowledge-capture`, `session-retrospective`).
- `session-retrospective` is the only knowledge-tier skill marked `user-invocable: true` and the only one using the `when_to_use` field (documented but unusual).

### 4.8 Size distribution

All 17 are under the 500-line budget. Three (`claim-discussion` 54 L, `ivy-error-patterns` 63 L, `propagation-patterns` 88 L) are under 100 lines and consist mostly of routers to `references/`. This is compatible with progressive disclosure but worth confirming each carries enough standalone value at load time.

### 4.9 References structure

No nested reference chains (depth never exceeds one from SKILL.md). Reference counts: ivy-toolkit (5), claim-discussion (3), ivy-writing-guide (3), reflection-patterns (6, including 5 critic prompts), ivy-error-patterns (2), specification-patterns (2), verify (2). Other skills with references have 1 file each. Five skills (`navigate`, `review`, `triage`, `session-retrospective`, `ivy-debugging-methodology`) ship no `references/` at all.

### 4.10 Content duplication hotspots

1. **Output Style block** — byte-identical in all 5 workflow skills.
2. **Iron Law + Staleness Rule** — near-identical in `verify` and `build`; distinct variants in `review` and `ivy-toolkit`.
3. **Workspace blockquote** (`> Workspace: Set active workspace with /set-workspace …`) — verbatim copies in 4 knowledge skills.
4. **MCP tool enumeration** — the five canonical `ivy_*` tool names appear in 11 SKILL.md files (~90 total mentions), with per-skill “when to use” guidance that is already canonical in `ivy-toolkit`.
5. **TaskCreate boilerplate** — present at the head of every workflow skill with the same shape and different strings.
6. **Top-5 error table** — present both in `ivy-error-patterns` and in `ivy-debugging-methodology`.
7. **RFC bracket-tag format** — documented in `.claude/rules/ivy-formatting.md` and re-stated in `methodology-reference` (9 times), `ivy-writing-guide`, `claim-discussion`, `review`.

### 4.11 README / CLAUDE.md self-consistency

- `skills/README.md` lists 14 skills (5 workflow + 9 knowledge) but the directory contains 17. Missing from the table: `ivy-debugging-methodology`, `ivy-error-patterns`, `session-retrospective`.
- Plugin `CLAUDE.md` lists 11 knowledge skills in the “Internal knowledge” sentence (includes `ivy-debugging-methodology` and `ivy-error-patterns`) but omits `session-retrospective`.
- `session-retrospective` is the only knowledge-tier skill marked `user-invocable: true` yet is not documented anywhere as a user entry point.
- README header still says “Knowledge Skills (9)”.

## 5. Prioritized, deduplicated recommendations

These combine per-skill and corpus-level findings. The order reflects the impact × effort heuristic: fix documentation and namespacing first (cheap), then structural deduplication, then missing skills.

1. **Reconcile `skills/README.md` with the 17 skills on disk.** Add `ivy-debugging-methodology`, `ivy-error-patterns`, and `session-retrospective` to the table. Update the “Knowledge Skills (9)” count. Decide whether `session-retrospective` belongs in a new “User-invocable reference” tier or should move to the workflow list.
2. **Fix skill-to-skill references to route through the Skill tool.** Known violations: `methodology-reference` (3 sites), `ivy-debugging-methodology` (1 site), `propagation-patterns` (1 site), `session-retrospective` (1 site), `review` (4 sites). Aligns with plugin convention `feedback_skill_cross_refs`.
3. **Fully-qualify all intra-plugin skill invocations.** `build` uses `Skill(skill="verify")` at line 229 while most other calls use `panther-ivy-plugin:<name>`. Standardize on the namespaced form.
4. **Extract shared boilerplate to `.claude/rules/`** or to a dedicated include-once skill. Targets (counts of copies): Output Style block (5×), Iron Law + Staleness Rule (3×), Workspace blockquote (4×), RFC bracket-tag rule (5×), TaskCreate step-tracking boilerplate (5×). Saves roughly 120 duplicate lines across workflow skills.
5. **Enforce `ivy-toolkit` as the single MCP-tool catalog.** Replace per-skill tool tables in `verify`, `build`, `review`, `triage`, and plugin CLAUDE.md with a single forward-reference, reducing the ~90 cross-file tool-name citations to a maintainable count.
6. **Add tables of contents to reference files >100 lines.** Confirmed missing: `ivy-toolkit/references/tool-catalog.md` (449 L), `methodology-reference/references/comprehensive-methodology-detail.md` (368 L), `specification-patterns/references/pattern-library-detail.md` (202 L), `knowledge-capture/references/knowledge-taxonomy.md` (158 L), `reflection-patterns/references/critic_prompts/g5_trace.md` (108 L). Anthropic best-practices call this out explicitly.
7. **Standardize knowledge-skill naming.** Either prefix every knowledge skill with `ivy-` or drop the prefix everywhere. Current mix (`ivy-error-patterns` vs `specification-patterns`, both pattern catalogs) is arbitrary.
8. **Resolve `knowledge-capture` ⇔ `session-retrospective` overlap.** Two user-facing entry points cover the same territory; the latter self-describes as a superset. Either fold in or sharply delineate their scopes in both `description` fields.
9. **Fix `reflection-patterns` description length.** Trim from 300 chars to ≤250 so the `Use when…` clause survives skill-listing truncation at the documented 1,536-char budget.
10. **Fill the IUT-output-analysis gap.** The 9-step procedure captured in user memory and in `verify/references/iut-output-analysis.md` should be promoted to a standalone `iut-analysis` knowledge skill so `build` and `triage` can load it too.
11. **Fill the coverage / traceability gap.** Create one `coverage-patterns` or `traceability-guide` knowledge skill that owns `ivy_coverage` (stats/gaps/matrix) + `ivy_extract_requirements` + `ivy_manifest`. Today that knowledge is fragmented across `review`, `claim-discussion`, and the `traceability-agent`.
12. **Declare `allowed-tools` on skills that prescribe tool use.** Targets: `counterexample-guide`, `methodology-reference`, `reflection-patterns`, `propagation-patterns`, `triage`, `review`. Keep the declaration minimal (name only the tools the body references).
13. **Document the `context: fork` convention.** State in the plugin README or skill-conventions rule when `context: fork` should be set. Currently 5 of 11 knowledge skills use it with no documented rule.
14. **Strengthen `review`'s description with concrete triggers.** Replace the generic phrasing with RFC-first keywords: `Audits Ivy models for RFC requirement traceability, structural quality, and coverage gaps. Use when verifying RFC compliance, assessing coverage matrices, or finding quality issues before verification.`
15. **Strengthen `triage`'s description with concrete error signals.** Replace “tools are broken” with `when MCP returns empty capabilities`, `when LSP diagnostics stop arriving`, `connection timeout`, `process not responding`.
16. **Fix the orphan `## Integration` heading in `ivy-writing-guide` (line 259).** Either populate or delete.
17. **Make G4/G5 verdict reporting in `verify` explicit.** Replace passive “critics audit whether `status: OK` reflects genuine soundness” with an imperative “Report to user: Gate verdict SOUND / UNSOUND(#NN) / ABSTAIN” step.
18. **Move narrative content out of `navigate`.** The Anti-Rationalization table belongs in `navigate/references/anti-rationalization.md` per `feedback_references_under_skill`.
19. **Restrict `session-retrospective`'s `Agent` permission.** Enumerate the permitted agent names rather than granting the unrestricted `Agent` tool.
20. **Harden Step 8 of `ivy-debugging-methodology`.** Reorder steps 1 and 2, and replace the “read `references/serializer-patterns.md`” path with a Skill-tool load of `ivy-writing-guide`.

## 6. Considerations

- **Pro**: The corpus is small enough (3,521 SKILL.md lines) that the 20-item backlog above can plausibly be executed in one coordinated pass. Progressive disclosure via `references/` is applied consistently where it exists; no SKILL.md exceeds the 500-line budget; no reference chain is deeper than one level. `ivy-error-patterns` is a standout example of correct structure — router SKILL.md + two provenance-tagged catalogs — and is worth using as the canonical template for future knowledge skills.
- **Con**: Much of the highest-value cleanup (Output Style boilerplate, Iron Law, MCP-tool enumeration) is structural and touches every workflow skill simultaneously. That work coordinates with the style-system hooks described in plugin CLAUDE.md §Style System; any extraction must be compatible with the `compose-style.py` hook and with how subagents inherit shared rules via CLAUDE.md.
- **Alternatives considered**:
  - *Merging `ivy-debugging-methodology` + `ivy-error-patterns` + `counterexample-guide` into a single debugging skill*. Rejected: the three split cleanly on input shape — generic error, catalogued pattern ID, counterexample trace — so the separation carries information. Fix the overlap with boundary rules instead of a merge.
  - *Leaving `session-retrospective` and `knowledge-capture` separate*. Rejected in favor of explicit scope reconciliation: two user-facing entry points with identical taxonomies confuse users; at minimum the `description` fields must make the split explicit.
  - *Keeping per-skill tool tables as a form of redundancy*. Rejected: with 90 cross-file tool citations, any tool rename becomes a multi-file patch; progressive disclosure via `ivy-toolkit` is cheaper and safer.
