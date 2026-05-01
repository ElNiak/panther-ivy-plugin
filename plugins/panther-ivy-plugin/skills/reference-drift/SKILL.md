---
name: reference-drift
description: "Use when auditing a plugin for broken cross-references — Skill()/Agent() calls, agent names cited in .claude/rules/, _KNOWN_* sets, tests, evals, hook imports — naming targets that no longer exist or were renamed."
user-invocable: true
version: "1.0.0"
---

# Reference Drift

**Type:** technique — apply procedurally; do not abridge the surface inventory step.

A *reference drift* is a string identifier in one file that no longer matches a registered name elsewhere in the plugin tree. Refactors rename `agents/foo-agent.md` to `agents/foo-bar-agent.md`, but the string `"panther-ivy-plugin:foo-agent"` survives in three other places — auto-loaded rules, dispatch boilerplate, test fixtures — and the rename is silently incomplete. The plugin still imports cleanly; the runtime breaks only when the dispatch path is exercised.

This skill teaches a procedure for finding every drift surface, the eight reference patterns to grep, the five drift classes, and the judgment call that distinguishes "intentional reserved name" from "orphan reference."

## When to use

- Before shipping a refactor that renamed any skill, agent, workflow, or rule.
- During a harness audit of a plugin's `skills/`, `agents/`, `hooks/`, `.claude/rules/`, `commands/`, `evals/`, `tests/`, or `scripts/` trees.
- After a CHANGELOG entry mentions "renamed", "moved", "consolidated", "deprecated", or "removed".
- When a runtime dispatch fails with "Unknown skill" or "agent not found" and you suspect more than one site is broken.

## When NOT to use

- For a single typo found via grep — fix it and move on.
- For style/cosmetic name drift the user has already approved (e.g., `.backup/` directories per the plugin's leave-alone convention; check `feedback_no_relocate_backup_files`).
- For mechanical lint that a regex hook can enforce (a PreToolUse hook would catch new dead `Skill()` references at write time; this skill is for the judgment-call audit, not the mechanical check).

## Phase 0 — Build canonical inventory FIRST

Before searching for broken references, build the canonical name set the audit will cross-check against. Without this, every reference-pattern grep result has to be cross-checked individually, and the audit either runs out of budget or trades old findings for new ones.

Run, in order:

```bash
ls <plugin>/skills/                # canonical skill names
ls <plugin>/agents/                # canonical agent names (strip .md)
grep -nE '_KNOWN_[A-Z]+\s*=' <plugin>/hooks/scripts/workflow_state.py
                                   # canonical workflow names + valid event types
grep -nE '"name":\s*"[^"]+"' <plugin>/.claude-plugin/plugin.json
                                   # canonical plugin name + version
```

Save the four name sets. Every reference pattern below cross-references against these. If a string in a reference site does not appear in any name set, it is a candidate drift. **Do not start grepping reference patterns until inventory is built.**

## Surface inventory — eight places drift hides

A naive auditor searches `*.md` and stops. Drift hides in seven other surfaces. **Search each, every audit:**

| # | Surface | Glob | What drifts |
|---|---|---|---|
| 1 | Skill bodies | `skills/**/*.md` | `Skill(skill="...")` calls, in-prose skill names |
| 2 | Agent bodies | `agents/*.md` | `Agent(subagent_type="...")` calls in operating procedures |
| 3 | Hook scripts (Python) | `hooks/scripts/*.py` | `Skill()`/`Agent()` strings in emitted text; `subprocess` invocations; matcher regexes |
| 4 | Hook scripts (shell) | `hooks/scripts/*.sh` | matcher patterns, exported env-var names, paths |
| 5 | Auto-loaded rules | `.claude/rules/*.md` | agents, skills, tools cited in body prose; tables of canonical names |
| 6 | Eval inputs | `evals/*.json` | paths in input strings, expected agent/skill outputs |
| 7 | Tests | `tests/test_*.py` | string literals, schema constants, `_KNOWN_*` sets |
| 8 | Top-level config | `plugin.json`, `routing-rules.json`, `hooks.json`, `.mcp.json` | activation paths, matchers, env names |

**Anti-pattern (RED-baseline finding):** the agent searches surfaces 1, 2, and (some of) 5 only, and reports "I found N broken references." It under-reports by 50–80%. Do not trust an audit that grepped only `.md` files.

## Reference patterns — eight queries to run

Run all eight for every audit. Each maps to a different drift class.

```bash
# 1. Skill() calls — runtime-fatal for the calling skill/hook
grep -rnE 'Skill\(skill="[^"]+"' --include='*.md' --include='*.py' <plugin>

# 2. Agent() dispatches — runtime-fatal for the calling workflow
grep -rnE 'Agent\(subagent_type="[^"]+"' --include='*.md' --include='*.py' <plugin>

# 3. Plugin-prefixed names in any context — catches in-prose mentions
grep -rnE 'panther-ivy-plugin:[a-z][a-z0-9-]+' <plugin>

# 4. Bare agent names in rule bodies — catches docs of dead agents
grep -rnE '\b(spec-analyst|plugin-conventions-reviewer|traceability-agent|...)\b' .claude/rules/

# 5. _KNOWN_* frozenset/dict definitions — catches stale schemas
grep -rnE '_KNOWN_[A-Z]+\s*=\s*(frozenset|set|\{)' <plugin>

# 6. Workflow strings in tests vs production — catches test-prod schema drift
grep -rnE 'workflow-(navigate|build|verify|review|triage)' tests/

# 7. Markdown subdirectory links — catches refactored-away dirs
grep -rnE '\]\([a-z][a-z0-9-]+/\)' --include='*.md' skills/

# 8. Dead `elif workflow == "..."` branches — catches code-level orphans
grep -rnE 'workflow\s*==\s*"[^"]+"' hooks/scripts/
```

For each match: cross-check against the on-disk inventory (`ls skills/`, `ls agents/`, etc.) using a single `git ls-files` pass first to build the canonical name set.

## Five drift classes — severity matrix

Classify every broken reference into one of these five classes; severity follows from the class.

| Class | Definition | Severity | Example |
|---|---|---|---|
| **Runtime-fatal** | The named target is invoked at runtime (`Skill(...)`, `Agent(...)`); call returns "Unknown skill / agent not found" | CRITICAL | `scaffold-ops/SKILL.md` Phase 5 dispatches `panther-ivy-plugin:traceability-agent` (no such agent — deferred per Task 1.0 of the bloat audit) |
| **Hook-emitted** | A hook script prints a string that names a non-existent target; the user/Claude is told to invoke something that does not exist | CRITICAL | `render-summary.py:253` prints `Skill(skill="panther-ivy-plugin:cross-cutting-knowledge-capture")` |
| **Documentation drift** | A non-code reference (auto-loaded rule, glossary, README) names an agent/skill that does not exist; not runtime-fatal but pollutes context every session | WARNING | `.claude/rules/agent-dispatch.md:10` cites `spec-analyst` (no such agent) |
| **Schema drift** | Tests, evals, or fixtures use an old name format that the production code no longer accepts | WARNING | `tests/test_workflow_state.py:155` declares `_KNOWN = {"workflow-verify", ...}`; production uses unprefixed `verify` |
| **Code-level orphan** | A Python `elif`, `case`, or dispatch table branch names a target that has been renamed; the branch is dead code | INFO | `hooks/scripts/render-summary.py:221` has `elif workflow == "navigate":` (orphan post-rename) |

## Judgment call — orphan vs intentional reserved name

Not every name that fails the inventory check is a bug. Some are intentionally retained.

**Decision procedure:**

1. **Read the surrounding comment / docstring.** If the file documents the name as intentional ("`navigate` is the orchestrator's internal flow name; do not remove from `_KNOWN_WORKFLOWS`"), it is reserved, not orphan. Do not flag.
2. **Check user feedback memory.** Some names are kept by deliberate user instruction. The plugin convention is to leave a `feedback_*` memory entry; grep `~/.claude/projects/.../memory/feedback_*` for the name. If it appears with "do not delete" or "deliberate placeholder" framing, leave alone.
3. **Check whether the name has a non-dispatch consumer.** A name in `_KNOWN_WORKFLOWS` may not need a corresponding skill — it might be the orchestrator's own internal state label. A name in a `description` example may be illustrative, not load-bearing.
4. **When in doubt, flag as INFO with rationale "appears intentional but cannot confirm without author input"** rather than CRITICAL. Then `AskUserQuestion` before proposing a removal patch.

**Anti-pattern:** treating every "missing" name as a CRITICAL drift and proposing a fix. The user's feedback memory `feedback_keep_insights_placeholder` is a documented case of "leave the apparent stub alone."

## Reporting format

**Per-surface accounting (mandatory).** Before listing findings, emit one line per surface stating either "N findings" or "verified clean":

```
| Surface                    | Result                          |
|----------------------------|---------------------------------|
| 1. Skill bodies            | 3 findings (see below)          |
| 2. Agent bodies            | 0 — verified clean              |
| 3. Hook scripts (Python)   | 1 finding                       |
| 4. Hook scripts (shell)    | 0 — verified clean              |
| 5. Auto-loaded rules       | 2 findings                      |
| 6. Eval inputs             | 1 finding                       |
| 7. Tests                   | N findings                      |
| 8. Top-level config        | 0 — verified clean              |
```

If you cannot honestly emit "verified clean" for a surface, you skipped it. Re-search before continuing.

**Then, per finding, emit:**

```
<surface>:<file>:<line> — <referenced-name> — <class> — <severity> — <rationale>
                       — fix: <patch description or "see <patch-id>">
```

Group findings by class so the user sees CRITICAL → WARNING → INFO in order.

**Final summary table:**

```
| Class               | Count |
|---------------------|------:|
| Runtime-fatal       |     N |
| Hook-emitted        |     N |
| Documentation drift |     N |
| Schema drift        |     N |
| Code-level orphan   |     N |
```

**Sanity check before submitting.** Sum your counts. If `total < (skills_count + agents_count) / 4` for a plugin under active refactor, you almost certainly missed a surface. Re-emit the per-surface accounting and re-search the surfaces with "verified clean" status.

## Common mistakes — observed in RED baseline

| Mistake | Reality |
|---|---|
| "Just grep `Skill(`" | Misses `Agent(...)`, in-prose mentions, hook-emitted strings, rule-cited names, schema fixtures. Six of eight surfaces ignored. |
| "Search `.md` only" | Hook scripts (`.py`, `.sh`), evals (`.json`), tests (`.py`) all carry drift. Inventory-then-cross-check beats single-extension grep. |
| "Found N broken refs, done" | The RED baseline found six; the full audit found fourteen. The 8/14 hit rate happens because surface coverage was incomplete. |
| "Test fixtures don't matter" | `_KNOWN = {"workflow-verify"}` in a test means production code that returns the unprefixed name fails the test — or the test passes against a backward-compat shim that violates `feedback_no_backward_compat_shims`. Either way, drift. |
| "If it's documented in a CHANGELOG, it's old, ignore" | Documentation drift in auto-loaded rules (`.claude/rules/`) is injected into context every session — it teaches Claude wrong names. Not "old", live. |
| "All dead refs are CRITICAL" | Reserved names exist (e.g., `navigate` in `_KNOWN_WORKFLOWS` is deliberate per its own comment). Apply the judgment-call decision procedure before classifying. |

## Red flags — STOP and re-audit

- You searched `*.md` only.
- You found < 8 broken references in a plugin with ~15 skills + 8 agents + 30 hooks under active refactor.
- You did not emit a per-surface accounting table at the top of the report.
- One or more surfaces is missing from the accounting table (you implicitly skipped it).
- You did not search `.claude/rules/` for in-prose agent names.
- You did not check `tests/` for schema constants.
- You did not check `hooks/scripts/*.py` for emitted Skill() strings.
- You traded findings — your CRITICAL count went up but your total went down compared to a quick `grep -rE 'panther-ivy-plugin:' --include='*.md'` pre-audit.
- You proposed a fix for `navigate` in `_KNOWN_WORKFLOWS` without checking the docstring above the definition.
- You did not group findings by class. (Runtime-fatal needs to be triaged before documentation drift; without classes, the user cannot prioritize.)

If any red flag fires: re-run the eight-pattern grep, re-classify into the five classes, re-emit the report **with per-surface accounting**.

## Recovery procedure when drift is found

1. **Inventory the canonical name set** for each surface (skills, agents, workflows, schemas) using a single `git ls-files` and `ls` pass.
2. **Build a rename map** from each broken reference to its closest existing target (or to "delete" if the target was retired without replacement).
3. **For runtime-fatal class only**: emit unified-diff patches inline. For documentation/schema drift: dispatch a meta-class agent to rewrite (the rewrite is too large for a hand-authored diff and benefits from semantic understanding, not just `sed`).
4. **Verify with grep** that the post-fix tree returns zero matches against the eight reference patterns.
5. **Append a `decision` journal entry** naming the rename map and the surfaces touched, so the next refactor has a record of which names were normalised.

## Integration

This skill is invoked from harness audits and from the `meta-self-mod-ops` workflow when a refactor renames any skill, agent, or workflow. It is **not** auto-dispatched from a hook — name drift detection is judgment-heavy (intentional vs orphan), and the eight-pattern grep is itself a slow operation; running it on every Write/Edit would dominate hook latency.

If a future PreToolUse hook lints `Skill()` and `Agent()` strings at write time, this skill remains for the broader surfaces (rules, evals, tests, schemas, code-level orphans) that no regex catches.
