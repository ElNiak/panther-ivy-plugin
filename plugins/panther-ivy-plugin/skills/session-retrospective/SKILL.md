---
name: session-retrospective
description: "Review session learnings and audit plugin skills/references for improvements. Use when a workflow completes, after 'what did we learn', 'improve skills', 'session retro', or 'what could be improved'."
user-invocable: true
allowed-tools: "Read Grep Glob Write Edit Agent AskUserQuestion Bash(git diff *) Bash(git log *) Bash(ls *)"
when_to_use: "Use when the user finishes a workflow session and wants to reflect on learnings, or when workflow completion gates suggest running a retrospective. Trigger phrases: 'what did we learn', 'improve skills', 'session retro', 'what could be improved', 'improve references', 'what should we remember'."
---

# Session Retrospective

Post-session review that captures learnings into the plugin knowledge base and audits existing skills and references for accuracy, completeness, and coverage gaps.

## Goal

Produce a structured report of (a) new learnings to persist and (b) skill/reference improvements, then apply user-approved changes to plugin files and user memory.

## Steps

### 1. Scan Session Context

Gather evidence of what happened during this session from all four sources:

1. **Active-workflow state**: Read `<protocol-dir>/.panther-ivy/active-workflow` to identify which workflow ran and what phase it reached.
2. **Session logs**: Read the most recent `.panther-ivy/session-logs/*.digest.yaml` files. If none exist, note this and proceed with other sources.
3. **Git diff**: Run `git diff --stat` and `git diff --name-only` to identify files modified during the session. For `.ivy` files, read the diffs to understand what changed.
4. **Conversation review**: Scan user messages for corrections ("no, not that", "don't do X"), steering ("actually, let's..."), and confirmations of non-obvious approaches. These are the highest-signal source for feedback learnings.

**Success criteria**: A clear list of (a) what was attempted, (b) what succeeded, (c) what failed or required correction, (d) what patterns were used.

### 2. Scan Existing Knowledge Base

Read all plugin knowledge files to know what's already documented:

- `.claude/rules/*.md` (all rule files)
- `CLAUDE.md` (plugin root)
- All `skills/*/SKILL.md` files (skill definitions)
- All `references/` files if they exist
- All `agents/` definitions

Build an index of covered topics, tool references, and pattern descriptions.

**Success criteria**: A mental map of what the plugin already knows, indexed by topic.

### 3. Classify Learnings

Invoke the `knowledge-capture` skill's classification approach:

1. For each candidate learning from Step 1, match against the knowledge taxonomy categories: bug patterns, Ivy patterns, architecture decisions, workflow refinements, emergent insights.
2. Diff each candidate against Step 2's index to determine: already documented (skip), partially documented (propose update), or new (propose addition).
3. Dispatch the classification reviewer agent (from knowledge-capture references) to recommend placement: plugin-rule, protocol-rule, or user-memory.

**Success criteria**: Each learning is classified with a category, target file, and placement recommendation.

### 4. Audit Skills and References

This is the novel layer beyond knowledge-capture. For each skill and reference in the plugin:

1. **Description accuracy**: Does the skill's `description` field still match what the skill actually does? Flag stale trigger phrases or missing use cases revealed by the session.
2. **Step accuracy**: Do the steps reference current tool names, correct MCP tool parameters, and valid file paths? Flag any step that contradicts what was observed during the session.
3. **Cross-reference validity**: Do skills reference other skills, agents, or files that still exist? Flag broken references.
4. **Reference currency**: Do reference docs reflect current Ivy patterns, tool capabilities, and methodology? Flag outdated content.
5. **Coverage gaps**: Identify patterns, workflows, or learnings from this session that NO existing skill or reference covers. These are candidates for new skills or reference additions.

Dispatch parallel agents for independent audit tasks (e.g., one for skill descriptions, one for reference docs) when the knowledge base is large.

**Success criteria**: A list of specific improvement recommendations, each with the target file, line/section, what's wrong, and proposed fix.

### 5. Present Report

Present findings in two sections via `AskUserQuestion`:

**Section A — New Learnings** (from Step 3):
```
N learning(s) detected:

1. "{learning text}"
   -> Category: {category}
   -> Placement: {target file}
   -> Reason: {why this is new/useful}
   -> (a) Approve  (b) Edit  (c) Reject  (d) Change target
```

**Section B — Skill/Reference Improvements** (from Step 4):
```
M improvement(s) identified:

1. {skill-name}/SKILL.md: {issue description}
   -> Proposed fix: {concrete change}
   -> (a) Approve  (b) Edit  (c) Reject

2. .claude/rules/{file}.md: {issue description}
   -> Proposed fix: {concrete change}
   -> (a) Approve  (b) Edit  (c) Reject
```

If nothing learnable or improvable is found, report that and exit.

**Human checkpoint**: The user must approve each item before changes are written.

**Success criteria**: User has reviewed and decided on every item.

### 6. Apply Approved Changes

For each approved item:

- **New learnings**: Write to the target rule file, protocol rule, or user memory using `Edit` (append to appropriate section). Update session digest with `status: approved`.
- **Skill improvements**: Edit the target SKILL.md with the approved fix. For description changes, verify the new description follows the skill-conventions rules (under 250 chars, front-loaded triggers, third person).
- **Reference improvements**: Edit the target reference file.
- **Coverage gaps (new skills)**: If the user approved a new skill recommendation, create a stub SKILL.md with the agreed name, description, and placeholder steps. Flag it for future development.

After all writes, run `git diff --stat` and present a summary of files changed.

**Success criteria**: All approved changes are written to disk. A summary of changes is presented.

## Auto-Suggestion Integration

Workflow completion gates (Completion Verification Gate in reflection-patterns) should suggest this skill when:
- The session involved more than 2 workflow phases
- The user made corrections during the session
- New patterns were used that don't appear in existing rules

The suggestion should be a simple `AskUserQuestion`: "Run a session retrospective to capture learnings and check for skill improvements?"

## Relationship to knowledge-capture

This skill is a superset of `knowledge-capture`. It reuses knowledge-capture's classification taxonomy and reviewer agent for the learning-capture portion (Steps 3 and part of 5-6), then adds the skill/reference audit layer (Step 4) which knowledge-capture does not cover. If only learning capture is needed (no skill audit), the existing `knowledge-capture` skill is sufficient.
