---
name: knowledge-capture
description: "Extract reusable lessons from the current session into plugin rules. Use when completing a workflow phase, after /nct-learn, or when a surprising fix or pattern emerges."
user-invocable: false
context: fork
allowed-tools: "Read Grep Glob Write Edit Agent AskUserQuestion Bash(ls *)"
---

# Knowledge Capture

Internal skill invoked by knowledge gates in workflow SKILLs. Extracts learnings from the current session, classifies them, and persists approved entries to plugin rules files or user memory.

## Pre-Check

If `invocation_depth > 0` in the active-workflow state, **skip this gate entirely** and return to the calling workflow. Knowledge gates must not interrupt sub-workflow calls.

## Step 1 — Scan Existing Knowledge

Read all target files to understand what is already documented:

- `.claude/rules/ivy-patterns.md`
- `.claude/rules/debugging.md`
- `.claude/rules/tool-reference.md`
- `.claude/rules/nct-methodology.md`
- `.claude/rules/insights.md`
- `CLAUDE.md` (plugin root)

Note key topics and patterns already covered. This prevents duplicate entries.

## Step 2 — Reflect on Session

Review what happened since the last knowledge gate (or session start). Look for:

1. **Bug patterns**: Errors diagnosed and fixed — what was non-obvious about the root cause?
2. **Ivy patterns**: `.ivy` code written that revealed a non-obvious construct or anti-pattern
3. **Architecture decisions**: Design choices made during build/review — layer organization, module composition, include structure
4. **Workflow refinements**: Multi-step sequences that were refined through trial and error, tool orderings discovered to matter
5. **Emergent insights**: Anything surprising that doesn't fit above — unexpected behaviors, cross-cutting observations

**If nothing learnable is found, exit silently.** Do not interrupt the user.

## Step 2b — Save Session Log

This runs unconditionally at every gate.

1. Read the current session's observability events from the JSONL log (resolve path via `IVY_OBSERVABILITY_DIR`, `IVY_WORKSPACE_ROOT/.observability/`, or `/tmp/ivy-observability/`).
2. Consolidate events into `.panther-ivy/session-logs/{timestamp}.json`.
3. Write a structured digest to `.panther-ivy/session-logs/{timestamp}.digest.yaml` using the schema from `references/knowledge-taxonomy.md`.

The digest captures: workflow type, protocol, phases reached, files modified, errors and resolutions, patterns applied, verification outcomes, and knowledge candidates from this gate.

## Step 3 — Classify Using Taxonomy

Load `references/knowledge-taxonomy.md`. For each candidate learning from Step 2, match against the 5 category recognition heuristics. Assign a primary category and a target file.

## Step 4 — Diff Against Existing

For each candidate, check the target file (read in Step 1):

- **Already documented**: Skip — the rule already covers this.
- **Partially documented**: Propose an update to the existing entry rather than a new one.
- **New knowledge**: Propose a new entry.

## Step 4b — Spawn Classification Reviewer Agent

Dispatch a parallel agent using the prompt template from `references/knowledge-taxonomy.md` (section "Classification Reviewer Agent Prompt"). Pass:

- The candidate list with proposed categories and targets
- The path to session digests: `.panther-ivy/session-logs/`
- The path to plugin rules: `.claude/rules/`

The agent returns a placement recommendation per candidate:
- `plugin-rule` + target file (generic, recurring, protocol-agnostic)
- `protocol-rule` + protocol (generic but protocol-scoped)
- `user-memory` (specific to current work)

Incorporate the agent's recommendations into the presentation.

## Step 5 — Draft and Confirm

Present each candidate via `AskUserQuestion`:

```
[Knowledge Gate] N learning(s) detected:

1. "{learning text}"
   -> Category: {category}
   -> Agent recommends: {placement} ({target file})
   -> Reason: {agent's reasoning summary}
   -> (a) Approve  (b) Edit  (c) Reject  (d) Change target  (e) Defer
```

For each user response:

- **(a) Approve**: Write the entry to the target file using `Edit` (append to the appropriate section). Update the digest's `knowledge_candidates` entry with `status: approved`.
- **(b) Edit**: Ask the user for the revised text via `AskUserQuestion`, then write.
- **(c) Reject**: Update the digest with `status: rejected`. Do not write.
- **(d) Change target**: Ask the user which file, then write there.
- **(e) Defer**: Update the digest with `status: deferred`. Re-present at the next knowledge gate.

## Deferred Candidate Handling

At the start of each gate (before Step 2), check the most recent digest for `status: deferred` candidates. If found, re-present them in Step 5 alongside any new candidates.

## Graduation Check (Emergent Insights)

After writing to `.claude/rules/insights.md`, check whether 3+ entries cluster around the same theme. If so, recommend promoting them: present the cluster to the user and suggest moving to the appropriate primary-category rule file.
