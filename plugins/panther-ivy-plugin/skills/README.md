# Skills

## Overview

- 6 skills providing domain knowledge for Ivy protocol testing within the PANTHER framework
- Skills are surfaced automatically by Claude Code when trigger patterns in the user's query match a skill's `description` frontmatter
- They provide **reference material** (language guides, workflow steps, tool catalogs); agents and commands provide interactive workflows and execution

## Skill Catalog

### Methodology

| Skill | Description |
|-------|-------------|
| [methodology-reference](methodology-reference/) | Complete reference for NCT (compositional testing), NACT (attack testing), and NSCT (simulation testing) methodologies |

### Specification Writing

| Skill | Description |
|-------|-------------|
| [specification-patterns](specification-patterns/) | 14-layer structural template and formal model pattern library (variants, serdes, shims, monitors, entities, modules) |
| [ivy-writing-guide](ivy-writing-guide/) | Ivy language syntax, declaration types, module system, test spec patterns, and RFC bracket-tag annotations |

### Tooling

| Skill | Description |
|-------|-------------|
| [tooling-reference](tooling-reference/) | Complete tool catalog: LSP operations, 15 MCP tools (consolidated with mode dispatch), Claude native tools, and coordination workflows |
| [ivy-lsp-walkthrough](ivy-lsp-walkthrough/) | End-to-end example of LSP + MCP coordination on the QUIC specification |

### Workflow

| Skill | Description |
|-------|-------------|
| [workflow-reference](workflow-reference/) | Verification workflows, RFC-to-Ivy mapping, quality gate pipeline, and debugging strategies |

## Learning Paths

### Path A: New to Ivy Protocol Testing

1. **methodology-reference** -- NCT approach, role inversion, 10-step workflow
2. **specification-patterns** -- 14-layer template, pattern library, scaffolding
3. **ivy-writing-guide** -- Ivy syntax, test specs, RFC annotations
4. **workflow-reference** -- Verification, debugging, quality gates

### Path B: Security Testing with NACT

1. **methodology-reference** -- NACT section: APT 6-stage lifecycle, attack entities
2. **ivy-writing-guide** -- Writing attack monitors with RFC bracket tags
3. **workflow-reference** -- Verification of attack model consistency

### Path C: Understanding the Tooling

1. **tooling-reference** -- Architecture (LSP + MCP + native), 15 consolidated tools, coordination workflows
2. **ivy-lsp-walkthrough** -- Concrete end-to-end example
3. **workflow-reference** -- Verify-debug-fix cycle

## Skill Details

### methodology-reference
- **Category**: Methodology
- **Purpose**: Complete reference for all three PANTHER methodologies: NCT (compositional testing with role inversion), NACT (APT 6-stage lifecycle security testing), and NSCT (Shadow NS simulation testing). Covers the 10-step NCT workflow, attack entity roles, and Shadow NS configuration.
- **Related commands**: `/nct-check`, `/nct-compile`, `/nct-scaffold`

### specification-patterns
- **Category**: Specification Writing
- **Purpose**: 14-layer structural template for protocol decomposition plus the formal model pattern library (variants, serdes, shims, monitors, entities, modules). Includes dependency graphs, minimal viable sets, scaffolding order, and composition rules.
- **Related commands**: `/nct-scaffold`, `/nct-add-pattern`

### ivy-writing-guide
- **Category**: Specification Writing
- **Purpose**: Ivy language syntax reference, test specification patterns (includes, exports, before/after, `_finalize`), and RFC bracket-tag annotation guide for traceability.

### tooling-reference
- **Category**: Tooling
- **Purpose**: Authoritative tool catalog for the 15 consolidated MCP tools (with mode/view/detail dispatch), LSP operations, and Claude native tools. Includes coordination workflows and enforcement rules.

### ivy-lsp-walkthrough
- **Category**: Tooling
- **Purpose**: End-to-end walkthrough: adding rfc9000:7.3 to the QUIC spec using LSP for navigation and MCP for analysis/verification.

### workflow-reference
- **Category**: Workflow
- **Purpose**: RFC-to-Ivy mapping patterns, verification workflows, quality gate pipeline, and debugging strategies.

## Skills vs Agents vs Commands

| Concept | Purpose | Invocation | Interaction |
|---------|---------|------------|-------------|
| **Skill** | Provides reference material and domain knowledge; surfaced automatically when trigger patterns match | Automatic (Claude Code matches user query to skill `description` frontmatter) | Passive -- informs the LLM's response with knowledge |
| **Agent** | Executes a multi-step interactive workflow using MCP tools and user input | `@agent-name` or selected by Claude Code when a task matches | Active -- calls tools, asks questions, produces artifacts |
| **Command** | Runs a single focused operation (verify, compile, scaffold) | `/command-name [args]` | Active -- executes one action and returns results |

### Available Agents (4)

| Agent | Purpose |
|-------|---------|
| model-reviewer | Reviews Ivy model files for quality, correctness, and best practices |
| methodology-guide | Interactive guide for NCT, NACT, and NSCT methodologies |
| spec-analyst | Navigates, explores, verifies, and diagnoses Ivy protocol specifications |
| traceability-agent | Extracts RFC requirements, creates manifests, and audits coverage |

### Available Commands (5)

| Command | Purpose |
|---------|---------|
| `/nct-add-pattern` | Add a formal model pattern to an existing protocol specification |
| `/nct-check` | Run formal verification (`ivy_check`) on an Ivy file |
| `/nct-compile` | Compile an Ivy file to a test executable (`ivyc`) |
| `/nct-model-info` | Display model structure (`ivy_show`) |
| `/nct-scaffold` | Scaffold a new protocol model or test specification |
