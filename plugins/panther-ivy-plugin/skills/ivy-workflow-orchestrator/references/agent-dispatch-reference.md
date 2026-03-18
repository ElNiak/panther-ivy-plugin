# Agent Dispatch Reference

## Per-Phase Agent Selection

| Phase | Agent | Context to Provide | Expected Output |
|---|---|---|---|
| 1 Explore | spec-analyst | protocol directory path, target file (if known) | Directory summary, include graph, existing coverage stats |
| 2 Plan | traceability-agent | RFC URL or text, target protocol name | Requirement manifest YAML with tag IDs |
| 3 Write | methodology-guide | Methodology (NCT/NACT/NSCT), layer plan, current layer | Writing guidance, pattern suggestions, best practices |
| 4 Verify | spec-analyst | File paths to verify, error output (if re-verifying) | PASS/FAIL report, error diagnosis, fix suggestions |
| 4 Verify | model-reviewer | File paths to review | Quality audit (ERROR/WARNING/INFO by severity) |
| 5 Finalize | traceability-agent | Manifest path + spec file paths | Coverage gaps report, statistics |

## Agent Dispatch Guidelines

### spec-analyst
- **Phase 1:** Use `Explore` mode — broad discovery, don't assume what exists
- **Phase 4:** Use `Verify` mode — focused diagnosis of specific failures
- **Tools available:** Read, Grep, Glob, Bash, Write, Edit, ToolSearch
- **Color:** blue

### traceability-agent
- **Phase 2:** Use `Extraction` mode — parse RFC normative language (MUST/SHOULD/MAY)
- **Phase 5:** Use `Review` mode — audit bracket-tag coverage against manifest
- **Tools available:** Bash, Read, Write, Edit, Glob, Grep, WebFetch, ToolSearch
- **Color:** orange

### methodology-guide
- **Phase 3 only:** Provide methodology context + current layer being written
- **Auto-detects:** NCT vs NACT vs NSCT from context
- **Tools available:** Read, Grep, Glob, Bash, Write, Edit, ToolSearch
- **Color:** cyan

### model-reviewer
- **Phase 4 only:** Run full quality checklist (structural, type safety, invariants, actions, initialization, organization)
- **Max iterations:** 3 review cycles before escalating
- **Tools available:** Read, Grep, Glob, ToolSearch (read-only)
- **Color:** magenta

### navigator
- **Not dispatched by orchestrator** — the navigator dispatches TO the orchestrator
- **Role:** Detect user intent and route to fast mode (direct tools) or deep mode (orchestrator)
- **Color:** green
