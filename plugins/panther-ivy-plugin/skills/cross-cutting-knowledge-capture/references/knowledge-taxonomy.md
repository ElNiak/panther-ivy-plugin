# Knowledge Taxonomy

Reference for the `knowledge-capture` skill. Defines 5 knowledge categories with recognition heuristics, persistence targets, entry formats, and negative examples.

## Category 1: Bug Patterns

**Recognition heuristics:**
- An error was encountered, root-caused, and fixed during the session
- The fix involved understanding something non-obvious about Ivy, MCP, Docker, or protocol behavior
- Detectable when: `ivy_verify` or `ivy_compile` failed, then succeeded after changes; or MCP/LSP errors were diagnosed and resolved

**Persistence targets:**
- Generic (protocol-agnostic, recurring): `skills/knowledge-verification-failures/references/debugging-environment.md` — append under "Common failures" or create a new subsection
- Specific (one-off, project-scoped): User memory (`~/.claude/projects/.../memory/`)

**Entry format:** One-liner: problem statement, root cause, fix.

**Example:**
```
- Z3 import error on ARM: stale libz3.so from apt conflicts with pip z3-solver. Fix: rm /usr/lib/libz3* before pip install.
```

---

## Category 2: Ivy Modelisation Patterns

**Recognition heuristics:**
- A non-obvious Ivy language construct was used or discovered
- An anti-pattern was found and corrected through verification feedback
- Detectable when: `.ivy` files were edited AND `ivy_verify` or `ivy_diagnostics` was called afterward

**Persistence target:** `.claude/rules/ivy-patterns.md` — add to existing sections or create new subsection.

**Entry format:** Pattern name, code snippet, when to use. Follow the existing format in `ivy-patterns.md` (code blocks with inline comments).

**Example:**
```ivy
# Always initialize relations in `after init` — omitting causes arbitrary values
relation conn_seen(C:cid)
after init { conn_seen(C) := false; }
```

---

## Category 3: Architecture Decisions

**Recognition heuristics:**
- A structural choice was made about layer organization, module composition, include graph structure, or shim design
- Detectable when: `build-state.yaml` was updated, MPE agents were consulted, or layer structure was discussed during the build workflow

**Persistence targets:**
- Generic (applies to all protocols): `.claude/rules/nct-methodology.md`
- Protocol-specific: Protocol-level documentation or a new protocol-scoped rule file

**Entry format:** Decision statement with rationale.

**Example:**
```
Shim isolates must re-export all actions from the entity layer — direct include from test specs breaks the assume-guarantee boundary.
```

---

## Category 4: Workflow Refinements

**Recognition heuristics:**
- A multi-step sequence was attempted, failed, then refined into a better sequence
- A tool ordering was discovered to be important
- Detectable when: the same tool was called multiple times with different parameters, or workflow phases were revisited

**Persistence targets:** `skills/knowledge-ivy-toolkit/references/tool-catalog.md` (tool-specific, including the journal event types subsection added 2026-04-22) or `skills/knowledge-verification-failures/references/debugging-environment.md` (triage-specific).

**Entry format:** Sequence description with ordering rationale.

**Example:**
```
Always run ivy_diagnostics(mode="structural") before ivy_verify — catches syntax errors in milliseconds vs seconds of wasted verification time.
```

---

## Category 5: Emergent Insights

**Recognition heuristics:**
- Does not fit categories 1-4 but represents knowledge worth preserving
- Unexpected tool behaviors, cross-cutting observations, correlations between unrelated components, performance characteristics discovered empirically
- "I wish I'd known this at the start of the session" moments
- The classification reviewer agent flags a candidate as "emergent" when it doesn't match primary recognition patterns but scores as recurring (2+ sessions) or high-impact

**Persistence target:** `.claude/rules/insights.md`

**Entry format:** Free-form observation with context tag.

**Example:**
```
- [cross-cutting] ivy_coverage reports 0% on files that use include chains deeper than 4 levels — the include graph resolver silently truncates. Workaround: flatten includes or use test_file scoping.
```

**Graduation rule:** When 3+ entries in `insights.md` cluster around the same theme, recommend promoting them to a proper category and moving them to the appropriate rule file.

---

## Negative Examples (do NOT capture)

- Ephemeral debugging steps that only apply to the current file state
- Patterns already documented in existing rules (detected by the diff step)
- One-off workarounds for infrastructure state that was subsequently fixed
- Task-specific progress notes (these belong in user memory project entries, not plugin rules)

---

## Classification Reviewer Agent Prompt

```
<role>
You are a Knowledge Classification Reviewer for the panther-ivy-plugin.
</role>

<artifact>
You will be given a list of candidate knowledge entries. Cross-reference them
against these four sources inside the workspace:
1. Past session digests in .panther-ivy/session-logs/*.digest.yaml (check recurrence)
2. Full event logs in .panther-ivy/session-logs/*.json (drill into when digests insufficient)
3. Existing plugin rules in .claude/rules/ (check for duplicates/updates)
4. Ivy model files in protocol-testing/ (check generality across protocols)
</artifact>

<check_procedure>
For each candidate, recommend placement:
- "plugin-rule" (generic, recurring, protocol-agnostic) + which rule file
- "protocol-rule" (generic but protocol-scoped) + which protocol
- "user-memory" (specific to current work context)
</check_procedure>

<output_schema>
For each candidate, return a placement recommendation under 200 words that
includes: recurrence count across sessions, similar existing rules found,
protocols where the pattern applies.
</output_schema>
```

---

## Digest Schema

```yaml
timestamp: "ISO-8601 UTC"
event_log: "{timestamp}.json"
workflow: verify|build|review|triage|navigate
protocol: quic|bgp|coap|minip|apt|apt_quic
phases_reached: [list of phase names reached]
files_modified: [list of .ivy file paths]
errors:
  - type: verification_failure|compile_error|mcp_error|lsp_error
    file: relative path
    error: error message summary
    resolution: what fixed it (if resolved)
patterns_applied: [list of pattern descriptions]
verification_outcomes:
  - file: relative path
    result: pass|fail
    attempts: N
knowledge_candidates:
  - category: bug-pattern|ivy-pattern|architecture|workflow|emergent
    content: the learning text
    status: approved|rejected|deferred
    target: target file path
```
