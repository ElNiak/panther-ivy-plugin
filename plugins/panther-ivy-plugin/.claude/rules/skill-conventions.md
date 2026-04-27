---
paths:
  - "**/panther-ivy-plugin/**/skills/**/SKILL.md"
  - "**/panther-ivy-plugin/**/agents/**/*.md"
---

<purpose>
Plugin-local skill authoring conventions. Takes precedence over the
worktree-level `.claude/rules/skill-conventions.md` for any path matched
by the globs above. Other plugins follow the worktree-level rule.
</purpose>

# Skill Conventions (panther-ivy-plugin)

## 0. Conflict resolution with the worktree-level rule

When both this rule and the worktree-level
`<repo-root>/.claude/rules/skill-conventions.md` are injected for the
same edit (their globs overlap on plugin SKILL.md / agent paths), the
plugin-local directives below are **authoritative** for paths under
`panther-ivy-plugin/`. The worktree-level rule's directives apply only
where this rule is silent — specifically: the SKILL.md body length cap
(under 500 lines, aim for 300), the per-skill `references/` placement
of heavy material, and the CSO checklist's mechanical-checks portion
(§7 below). On any contradicting directive — most notably the
description format (§1 below directly contradicts the worktree-level
"what it does + Use when…" template) — this rule wins.

The harness has no priority machinery for path-scoped rules; both rule
bodies land in the prompt context together. This §0 is the explicit
resolution rule the reader applies to break the tie.

## 1. Frontmatter description format — trigger-only imperative

Skill `description` fields lead with the trigger ("You MUST use this when…"
for rigid workflow skills, "Use when…" for flexible pattern skills) and
end with a single-sentence outcome statement.

```yaml
# rigid workflow skill
description: "You MUST use this when starting a new Ivy spec, scaffolding a layer, or resuming an in-progress build. Builds protocol specification layers from RFC."

# flexible pattern skill
description: "Use when authoring or editing .ivy files. Provides Ivy 1.7 syntax reference, module-system patterns, RFC annotation rules, and test-spec checklists."
```

**Why trigger-first:** Per the upstream skill-trigger research summarized in
the worktree-level rule, leading with the use-case improves Claude's
compliance with skill invocation gates. Rigid workflow skills additionally
use "You MUST use this" to reflect their iron-law-bound discipline; flexible
pattern skills retain the milder "Use when…" because they are reference
material, not enforced sequences.

This shape OVERRIDES the worktree-level rule's "what it does + Use when…"
template for this plugin's skills. Cross-plugin consistency is sacrificed
deliberately in favor of plugin-internal compliance signal.

## 2. Skill-type declaration — body line under the top heading

Every `SKILL.md` declares its type immediately after the top-level heading
(or after the `<role>` block if one is present), before any `## ...` section:

```markdown
**Type:** rigid — follow exactly, do not adapt away discipline.
```

or:

```markdown
**Type:** flexible — adapt principles to context.
```

**Rigid (6):** `build`, `verify`, `review`, `triage`, `navigate`,
`knowledge-capture`. These are workflow skills bound by iron laws and
adversarial gates; deviation is a soundness risk.

**Flexible (11):** `ivy-writing-guide`, `ivy-error-patterns`,
`methodology-reference`, `specification-patterns`, `apt-attack-patterns`,
`ivy-toolkit`, `propagation-patterns`, `counterexample-guide`,
`claim-discussion`, `ivy-debugging-methodology`, `reflection-patterns`.
These are pattern/reference skills consumed by the rigid workflows and by
the user.

## 3. HARD-GATE markup — pre-action enforcement directives

Where a workflow skill needs to halt action until a precondition is cleared,
wrap the directive in a `<HARD-GATE>` block at the top of the relevant
phase (or step) section. HARD-GATE is decision-time enforcement; it is
complementary to and does not replace:

- `<iron-law name=… enforcement=…/>` tags (declarative binding to canonical
  iron-law text in `.claude/rules/iron-laws.md`)
- `[GAP: #NN reason]` markers (post-hoc unsoundness annotations written by
  adversarial gate verdicts; lifecycle in `.claude/rules/gap-markers.md`)

```markdown
## Phase 3 — Implement layer

<HARD-GATE>
Do NOT proceed if G1 verdict is not SOUND. NO_LAYER_WITHOUT_SCAFFOLD binds:
ivy_diagnostics(mode=structural) MUST be SOUND on the predecessor layer
before Write/Edit on layer N.
</HARD-GATE>

<iron-law name="NO_LAYER_WITHOUT_SCAFFOLD"
  enforcement="ivy_diagnostics precondition in Phase 3"/>
```

Place HARD-GATEs at action-decision boundaries (entering a new phase,
dispatching a critic, claiming completion), not at informational headings.

## 4. Red Flags rationalization tables — required for rigid workflow skills

Every rigid workflow `SKILL.md` includes a `## Red Flags` section mapping
plausible-but-wrong rationalizations to their reality. The table targets
Ivy-specific failure modes the workflow has historically encountered:

```markdown
## Red Flags

| Thought | Reality |
|---|---|
| "ivy_verify SOUND, we're done" | G4 critic verdict required before claim. SOUND alone is necessary but not sufficient. |
| "The IUT trace matches, skip pcap" | Ivy log events do not guarantee wire transmission. Cross-validate pcap. |
```

If the table grows past ~15 rows, move the body to
`skills/<name>/references/red-flags.md` and keep a 5-row "top hits" summary
in `SKILL.md` with a Read pointer to the references file.

Flexible pattern skills do not need a Red Flags table; their reference
nature is self-disciplining.

## 5. Process diagrams — required for rigid workflow skills

Every rigid workflow `SKILL.md` includes a `## Process Flow` section with a
Graphviz `digraph` block diagramming the phase decision flow. Diamonds for
decisions, boxes for actions, doublecircle for entry/exit, labeled edges
for branches. Diagrams supplement (do not replace) the prose phase
descriptions.

Flexible pattern skills do not need a `## Process Flow`; their structure
is reference-driven, not flow-driven.

## 6. Step Tracking — required for rigid workflow skills

Every rigid workflow `SKILL.md` includes a `## Step Tracking` section
showing the exact `TaskCreate` calls to issue at the start of each phase.
The harness's `TaskCreate` / `TaskUpdate` tools are the load-bearing
tracking mechanism; the Step Tracking section is what tells Claude to use
them.

```markdown
## Step Tracking

At the start of each phase, create tasks for each step using `TaskCreate`.
Mark each `in_progress` before executing and `completed` after.

Phase 1 (Scope):
\```
TaskCreate(subject="Detect methodology context", activeForm="Detecting methodology")
TaskCreate(subject="Identify target protocol and RFC", activeForm="Identifying target")
\```
```

## 7. CSO checklist (carry-over from worktree-level rule)

Before finalizing a SKILL.md description: contains concrete trigger
phrases, exact error strings for error-handling skills, third person
where applicable, no workflow summary in the description, under 250
chars, synonyms covered.

Body length cap from the worktree-level rule still applies: SKILL.md
under 500 lines, aim for under 300 for frequently-loaded skills. Move
heavy reference material to `references/` subdirectory.
