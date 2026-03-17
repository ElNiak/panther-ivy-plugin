# Agents

## Overview

This directory contains 4 specialized Claude Code agents for Ivy protocol testing tasks within the PANTHER framework. Each agent is defined as a Markdown file with YAML frontmatter specifying its name, description, example triggers, available tools, and color.

Agents are invoked automatically when the user's request matches a trigger pattern described in the frontmatter `description` field, or explicitly by referencing the agent name.

## Agent Selection Guide

| Task | Agent | Methodology |
|------|-------|-------------|
| NCT/NACT/NSCT methodology guidance, specification writing | `methodology-guide` | All |
| Review Ivy model quality, pre-commit validation | `model-reviewer` | All |
| Navigate specs, verify, compile, diagnose failures | `spec-analyst` | All |
| Extract RFC requirements, audit coverage, traceability gaps | `traceability-agent` | All |

## Agent Details

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
- **ivy-tools MCP** -- 15 consolidated tools including `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_lint`, `ivy_coverage` (mode=matrix/stats/gaps/diff), `ivy_query` (mode=impact/xrefs/info), `ivy_visualize` (view=dependencies/state_machine/layers), `ivy_quality` (mode=suggestions/gate), `ivy_patterns` (mode=analyze/validate/compare/check) configured via `.mcp.json`

See the `spec-analyst` agent for the protocol model directory.

A `PreToolUse` hook (`hooks/scripts/block-direct-ivy.sh`) intercepts all `Bash` tool calls and warns about direct invocations of `ivy_check`, `ivyc`, `ivy_show`, and `ivy_to_cpp`. If a warned command is detected, the hook prints a message suggesting the corresponding MCP tool:

| Warned CLI command | Required MCP tool |
|---------------------|-------------------|
| `ivy_check` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` |
| `ivyc` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
| `ivy_show` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` |
| `ivy_to_cpp` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
