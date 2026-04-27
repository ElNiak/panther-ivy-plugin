# Knowledge-Capture — Skill & Reference Audit Checklist

Cold-path detail extracted from `knowledge-capture/SKILL.md` Step 4.5 so
the session-loaded skill stays lean. Load this file when Step 4.5 fires
(top-level user retrospective, `invocation_depth == 0`) and you need the
full audit checklist plus dispatch guidance.

## When it runs

Step 4.5 only runs when `invocation_depth == 0` in the active-workflow
state — i.e., a top-level user-triggered retrospective, not a workflow-gate
invocation. When it's skipped, knowledge-capture proceeds directly to
Step 5 with Section A (new learnings) only; Section B (skill/reference
improvements) is empty.

## The 5-item audit checklist

For each skill and reference in the plugin:

1. **Description accuracy**: Does the skill's `description` field still match what the skill actually does? Flag stale trigger phrases or missing use cases revealed by the session.
2. **Step accuracy**: Do the steps reference current tool names, correct MCP tool parameters, and valid file paths? Flag any step that contradicts what was observed during the session.
3. **Cross-reference validity**: Do skills reference other skills, agents, or files that still exist? Flag broken references.
4. **Reference currency**: Do reference docs reflect current Ivy patterns, tool capabilities, and methodology? Flag outdated content.
5. **Coverage gaps**: Identify patterns, workflows, or learnings from this session that NO existing skill or reference covers. These are candidates for new skills or reference additions.

## Parallel dispatch

Dispatch parallel agents for independent audit tasks (e.g., one for skill
descriptions, one for reference docs) when the knowledge base is large.
Each agent gets a clean context and a narrow audit scope so findings come
back focused.

## Output format

A list of specific improvement recommendations, each with:

- target file (skill `SKILL.md`, agent `.md`, or reference `.md`)
- target line or section within the file
- what's wrong (stale phrase, broken link, outdated pattern, coverage gap)
- proposed fix (concrete rewrite suggestion or reference pointer)

These results feed Section B of Step 5 in the SKILL body.
