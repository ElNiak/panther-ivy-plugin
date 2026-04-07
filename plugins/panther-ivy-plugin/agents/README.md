# Agents

## Overview

This directory contains 5 specialized Claude Code agents for Ivy protocol testing tasks within the PANTHER framework. Each agent is defined as a Markdown file with YAML frontmatter specifying its name, description, example triggers, available tools, and color.

Agents are invoked automatically when the user's request matches a trigger pattern described in the frontmatter `description` field, or explicitly by referencing the agent name.

**All agents are now interactive.** They reference the `interaction-patterns` and `claim-discussion` skills for structured user engagement during analysis workflows. The `navigator` agent serves as the primary entry point.

## Agent Selection Guide

| Task | Agent | Methodology |
|------|-------|-------------|
| Don't know where to start, need guidance | `navigator` | All |
| NCT/NACT/NSCT methodology guidance, specification writing | `methodology-guide` | All |
| Review Ivy model quality, pre-commit validation | `model-reviewer` | All |
| Navigate specs, verify, compile, diagnose failures | `spec-analyst` | All |
| Extract RFC requirements, audit coverage, traceability gaps | `traceability-agent` | All |

## Orchestrator Phase Dispatch

When agents are dispatched by the `ivy-workflow-orchestrator` skill, they operate in a specific phase context:

| Phase | Agent | Focus |
|-------|-------|-------|
| 1 Explore | spec-analyst | Discovery — directory layout, include graph, coverage stats |
| 2 Plan | traceability-agent | RFC requirement extraction, manifest generation |
| 3 Write | methodology-guide | Writing guidance, pattern suggestions, Ivy syntax review |
| 4 Verify | spec-analyst | Error diagnosis, counterexample interpretation |
| 4 Verify | model-reviewer | Quality audit (structural, type safety, invariants) |
| 5 Finalize | traceability-agent | Coverage audit, gap reporting, statistics |

All agents also operate in **fast mode** (outside orchestrator) for direct user requests.

## Agent Details

### navigator

**Purpose:** Adaptive entry point for Ivy protocol testing workflows. Detects user expertise, goals, and workspace context through a minimal adaptive interview, then routes to the appropriate specialist agent.

**When to use:**
- User asks "What should I do next?" or needs workflow guidance
- User is unsure which agent or tool to use
- Starting a new testing workflow from scratch

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

**Skills referenced:** `adaptive-interview`, `interaction-patterns`, `claim-discussion`

---

### methodology-guide

**Purpose:** Expert guide for all three PANTHER testing methodologies: NCT (compositional testing), NACT (attack testing), and NSCT (simulation testing). Detects from context which methodology the user needs.

**When to use:**
- Creating a new formal specification for a protocol
- Working through the NCT 10-step workflow, NACT APT lifecycle, or NSCT simulation setup
- Writing before/after monitors that encode RFC requirements
- Designing attack entities or configuring Shadow NS topologies

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

---

### model-reviewer

**Purpose:** Expert reviewer of Ivy formal specification models. Analyzes `.ivy` files for correctness, completeness, and adherence to best practices. Reports findings organized by severity (ERROR / WARNING / INFO). Read-only -- does not modify files.

**When to use:**
- Quality review of Ivy models before committing changes
- Checking invariant quality and modeling concerns
- Detecting anti-patterns: unguarded `assume`, missing invariants, deeply nested quantifiers

**Tools available:** `Read`, `Grep`, `Glob`, `ToolSearch`

---

### spec-analyst

**Purpose:** Specification navigator, verifier, and diagnostician. Handles both exploration (navigate, explain, trace dependencies) and verification (formal checking, compilation, error diagnosis).

**When to use:**
- Onboarding to an existing protocol model
- Verifying Ivy specs and diagnosing compilation errors
- Tracing include dependencies and cross-referencing failures

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

---

### traceability-agent

**Purpose:** RFC requirement extraction and traceability review specialist. Extracts requirements from RFC text, generates YAML manifests, and audits coverage gaps.

**When to use:**
- Extracting normative requirements from RFC text
- Creating or updating `*_requirements.yaml` manifest files
- Identifying uncovered RFC requirements and orphaned tags

**Tools available:** `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `ToolSearch`

---

## MCP Tool Enforcement

All agents use two tool sources:
- **Claude's native tools + Ivy LSP** -- Code navigation (`Read`, `Grep`, `Glob`, `Edit`, `Write`) and Ivy-specific LSP features (go-to-definition, find-references, hover) configured via `.lsp.json`
- **ivy-tools MCP** -- 22 MCP tools (see CLAUDE.md for the full reference table) configured via `.mcp.json`

**Available Protocol Models:**
- **QUIC** (complete, 202+ files) — `protocol-testing/quic/`
- **BGP** (partial) — `protocol-testing/bgp/`
- **CoAP** (partial) — `protocol-testing/coap/`
- **HTTP** (minimal) — `protocol-testing/http/`
- **MiniP** (partial, flat structure) — `protocol-testing/minip/`
- **System** (system-level specs: entities, network, protocols) — `protocol-testing/system/`
- **new_prot** (template, empty files) — `protocol-testing/new_prot/`
- **APT** (cross-cutting attacks) — `protocol-testing/apt/`

A `PreToolUse` hook (`hooks/scripts/block-direct-ivy.sh`) intercepts all `Bash` tool calls and warns about direct invocations of `ivy_check`, `ivyc`, `ivy_show`, and `ivy_to_cpp`. If a warned command is detected, the hook prints a message suggesting the corresponding MCP tool:

| Warned CLI command | Required MCP tool |
|---------------------|-------------------|
| `ivy_check` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` |
| `ivyc` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
| `ivy_show` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` |
| `ivy_to_cpp` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
