# Graduation Sweep

The graduation sweep walks the project auto-memory directory, clusters feedback entries by topic, and promotes them to skill references or rule updates with per-target user approval. It also archives stale entries and deletes exact duplicates.

## Triggers

The sweep is invoked by any of:

- `/nct-learn` slash command with sweep intent.
- End-of-session retrospective when the user opts in.
- navigate's Phase 1 Step 2b.1 advisory fires (days-since-last-sweep exceeds the configured threshold).

Nothing auto-runs the sweep. The advisory in navigate is informational; the user decides when to invoke.

## Memory directory

`~/.claude/projects/<project>/memory/`. The `<project>` segment is derived from the git repo. Entries live directly in this directory; historical archives live in `memory/historical/`.

## Phase 1 — Walk memory

Enumerate every `.md` file under `memory/` excluding `memory/historical/`. Record for each:

- Path.
- Title (from `name:` frontmatter or filename).
- Date (from the `Active Work (YYYY-MM-DD)` section heading that lists it in `MEMORY.md`, or file mtime as fallback).
- Size (line count).
- Primary category (from `type:` frontmatter: user, feedback, project, reference).

Exclude `memory/MEMORY.md` (the index) from candidate classification; it is updated at Phase 5.

## Phase 2 — Classify into target classes

For each entry, determine exactly one target class:

### GRADUATION

The entry's content clusters with 3+ other entries on the same theme, and the cluster maps cleanly to an existing skill reference or rule. Canonical cluster mappings (derived from the knowledge-taxonomy):

| Cluster theme | Target |
|:--|:--|
| Ivy language patterns (QUIC / BGP generators, serializers, solver mechanics) | `skills/knowledge-ivy-writing-guide/references/ivy-1.7-patterns-reference.md` (or `.claude/rules/ivy-patterns.md` if the content is primitive syntax) |
| Tool invocation discipline (ivyc vs panther run, compile-first, background verification) | `skills/knowledge-ivy-toolkit/references/tool-catalog.md` |
| IUT output analysis (pcap cross-validation, 9-step analysis) | `skills/workflow-verify/references/iut-output-analysis.md` or `skills/knowledge-ivy-debugging-methodology/references/debugging-environment.md` |
| Adversarial-gate lifecycle (gates at exploration/blueprint/etc.) | `.claude/rules/iron-laws.md` or `skills/cross-cutting-reflection-patterns/references/gates.md` |
| Docker / build infrastructure (ARM64, mirrors, Rosetta) | Stay in memory; these are environment-specific and not general plugin knowledge. |

### ARCHIVE

The entry is older than 60 days AND its referenced state (commits, files, issues) is committed/pushed/closed. Criteria:

- Entry file mentions a commit hash that resolves in `git log`.
- Entry mentions "committed", "pushed", "merged", or "closed" in its body.
- Entry was tagged "likely stale" in `MEMORY.md`.

Target: `memory/historical/`. Preserve the filename.

### DELETE

The entry is an exact duplicate of another entry, an empty placeholder never populated, or has been explicitly superseded by a later entry.

Target: removed from `memory/`. Tracked in git history for recovery.

### RETAIN

The entry is current, does not cluster with 3+ others, and is not stale. No action.

## Phase 3 — Present per-target approval

Group candidates by destination file. For each target, call `AskUserQuestion` with an option set:

```
Question: "Target: <destination-path>. N candidate entries ready to promote. How do you want to handle this target?"
Options:
  - approve all — apply the promotion/archive/delete to every candidate for this target
  - reject all — skip this target; leave candidates in memory
  - show each — walk candidates individually with per-entry approve/reject
  - skip target — defer to next sweep
```

For "show each", loop with a per-entry `AskUserQuestion` showing the entry's title, date, and proposed action.

Order targets as: (1) GRADUATION targets, (2) ARCHIVE targets, (3) DELETE targets. The user is most likely to engage with promotions; archives/deletes are lower-stakes and can be batched.

## Phase 4 — Apply approved changes in three commits

Group approved changes by commit boundary.

**Commit 1 — Graduations.** For each approved graduation target:
- Append the clustered content to the target file under a new named section (use the cluster theme as the heading).
- Remove the source entries from `memory/`.
- Update `MEMORY.md` index — remove the promoted entries from their `Active Work` or `Feedback` section; optionally add a one-line note under `References` pointing at the target file.

Commit message template:
```
docs(plugin-memory): graduate N entries to <target-file>

Promoted entries:
- <entry-1>
- <entry-2>
...

Cluster theme: <theme>
```

**Commit 2 — Archives.** Move approved archive candidates to `memory/historical/`. Update `MEMORY.md` to remove entries from active sections.

Commit message:
```
chore(plugin-memory): archive N stale entries

Archived (moved to historical/):
- <entry-1>
- <entry-2>
...
```

**Commit 3 — Deletes.** Remove approved delete candidates. Update `MEMORY.md`.

Commit message:
```
chore(plugin-memory): delete N duplicate/empty entries

Removed:
- <entry-1> (duplicate of <other>)
- <entry-2> (empty placeholder)
...
```

Each commit is independent. If Commit 2 fails review after the fact, it can be reverted without affecting Commits 1 or 3.

## Phase 5 — Update `MEMORY.md`

Edit the line `Last graduation sweep: YYYY-MM-DD` at the top of `MEMORY.md` to today's date. If the line is missing (first sweep), add it directly after the `# PANTHER Project Memory` heading.

This is a final, separate commit:
```
chore(plugin-memory): record sweep completion date
```

## Phase 6 — Dispatch drift-defense audit

Dispatch one `Explore` sub-agent with this exact prompt:

> grep for duplicated `^#{1,3} ` headings across:
> - `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.claude/rules/*.md`
> - `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/*/references/*.md`
> - `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/*/SKILL.md`
>
> Report any heading that appears in 2+ files with file:line locations. Exclude YAML frontmatter. Do not flag legitimate cross-references (where one file's heading is a citation pointer to another's canonical content). Under 300 words.

Include the agent's findings in the sweep's closing report as a "Drift audit" section.

## Phase 7 — Closing report

Print a summary to the user:

```
## Graduation sweep — 2026-04-23

- Graduations applied: N
- Archives applied: N
- Deletes applied: N
- Retained (no action): N

## Drift audit findings

<verbatim from Phase 6 agent response>

## Next recommended sweep

2026-05-07 (+14 days from today).
```

The closing report is displayed but not committed to a file.

## Edge cases

- **Sweep interrupted mid-way.** Approved commits stand. Re-invoking picks up remaining candidates on re-classification. `MEMORY.md` is updated only when all phases complete.
- **Cluster ambiguity.** An entry that could graduate to two targets appears in the first target's candidate list; the user rejects it there and approves it at the correct target. The classification phase proposes one canonical target; the approval phase is the correction point.
- **Active Work entries.** `MEMORY.md` sections tagged `Active Work (YYYY-MM-DD)` are not archived unless entries explicitly reference committed/pushed/merged/closed work. Work-in-progress stays.
- **Drift audit finds a legitimate cross-reference.** The audit's output is advisory. Legitimate cross-citations (e.g., a skill body's "## Iron Laws" section that pointer-cites the rule) are not drift. The user decides.
