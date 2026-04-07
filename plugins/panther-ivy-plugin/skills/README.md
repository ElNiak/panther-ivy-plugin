# Skills

## Overview

- 20 skills providing domain knowledge for Ivy protocol testing within the PANTHER framework
- Skills are surfaced automatically by Claude Code when trigger patterns in the user's query match a skill's `description` frontmatter
- They provide **reference material** (language guides, workflow steps, tool catalogs); agents and commands provide interactive workflows and execution

## Workflow Architecture: Fast/Deep Mode

All skills operate in one of two modes:

- **FAST mode** — Direct tool invocation for simple tasks (check a file, query model info, explore a concept). No orchestrator required.
- **DEEP mode** — Multi-phase workflow for spec creation/modification. Chains through the `ivy-workflow-orchestrator` skill which enforces 5 phases: Explore → Plan → Write → Verify → Finalize.

```
                    ivy-workflow-orchestrator
                    ┌──────────────────────────────┐
                    │ Phase 1: EXPLORE              │
                    │   loads: ivy-toolkit           │
                    │   loads: [methodology] skill   │
                    │   dispatches: spec-analyst     │
                    ├──────────────────────────────┤
                    │ Phase 2: PLAN                 │
                    │   loads: specification-patterns │
                    │   loads: workflow-reference     │
                    │   dispatches: traceability-agent│
                    ├──────────────────────────────┤
                    │ Phase 3: WRITE                │
                    │   loads: ivy-writing-guide      │
                    │   loads: incremental-spec-dev   │
                    │   dispatches: methodology-guide │
                    ├──────────────────────────────┤
                    │ Phase 4: VERIFY               │
                    │   loads: workflow-reference     │
                    │   dispatches: spec-analyst      │
                    │   dispatches: model-reviewer    │
                    ├──────────────────────────────┤
                    │ Phase 5: FINALIZE             │
                    │   dispatches: traceability-agent│
                    └──────────────────────────────┘
```

## Skill Catalog

### Orchestration & Tooling

| Skill | Description |
|-------|-------------|
| [ivy-workflow-orchestrator](ivy-workflow-orchestrator/) | Central 5-phase engine with iron laws — enforces explore → plan → write → verify → finalize |
| [ivy-toolkit](ivy-toolkit/) | Single source of truth for all MCP tool documentation and tool selection guidance |

### Methodology

| Skill | Description |
|-------|-------------|
| [methodology-reference](methodology-reference/) | Comprehensive reference for all three PANTHER methodologies (NCT, NACT, NSCT) with full workflows, red flags, common mistakes, and directory structures |
| [nct-methodology](nct-methodology/) | NCT: specification-based protocol compliance testing, 10-step workflow, role inversion |
| [nact-methodology](nact-methodology/) | NACT: security testing with APT 6-stage lifecycle, attack entities |
| [nsct-methodology](nsct-methodology/) | NSCT: Shadow Network Simulator, deterministic execution, topology control |

### Specification Writing

| Skill | Description |
|-------|-------------|
| [specification-patterns](specification-patterns/) | 14-layer structural template and formal model pattern library (variants, serdes, shims, monitors, entities, modules) |
| [ivy-writing-guide](ivy-writing-guide/) | Ivy language syntax, declaration types, module system, test spec patterns, and RFC bracket-tag annotations |
| [incremental-spec-dev](incremental-spec-dev/) | Add-verify-iterate loop for incremental formal specification development |
| [counterexample-guide](counterexample-guide/) | Interpreting ivy_verify counterexample traces and identifying fixes |

### Tooling

| Skill | Description |
|-------|-------------|
| [ivy-lsp-walkthrough](ivy-lsp-walkthrough/) | End-to-end example of LSP + MCP coordination on the QUIC specification |
| [lsp-patterns](lsp-patterns/) | LSP invocation patterns for validation and health-check contexts |

### Workflow

| Skill | Description |
|-------|-------------|
| [workflow-reference](workflow-reference/) | Verification workflows, RFC-to-Ivy mapping, quality gate pipeline, and debugging strategies |

### Interaction

| Skill | Description |
|-------|-------------|
| [interaction-patterns](interaction-patterns/) | Reusable checkpoint types (Gate, Inform-and-Continue, Collaborative), question formats, and adaptive follow-up rules for consistent user interaction across all agents |
| [claim-discussion](claim-discussion/) | Structured decision trees for verification claim resolution, RFC requirement mapping, and coverage gap prioritization |
| [adaptive-interview](adaptive-interview/) | Navigator agent's interview logic: context detection, goal identification, methodology selection, target scoping, and dispatch |

### Utility

| Skill | Description | Category |
|-------|-------------|----------|
| `healthcheck` | Fast triage of Ivy MCP sidecar & LSP stack health | Utility |
| `ivy-protocol-model-builder` | Interactive 6-phase workflow for creating new formal Ivy protocol specifications | Process |
| `propagation-patterns` | Patterns for propagating type changes across ser/deser state machines | Reference |
| `workspace-management` | Set, clear, and auto-detect active Ivy protocol workspace | Utility |

## Learning Paths

### Path A: New to Ivy Protocol Testing

1. **methodology-reference** → **nct-methodology** -- NCT approach, role inversion, 10-step workflow
2. **specification-patterns** -- 14-layer template, pattern library, scaffolding
3. **ivy-writing-guide** -- Ivy syntax, test specs, RFC annotations
4. **workflow-reference** -- Verification, debugging, quality gates

### Path B: Security Testing with NACT

1. **methodology-reference** → **nact-methodology** -- APT 6-stage lifecycle, attack entities
2. **ivy-writing-guide** -- Writing attack monitors with RFC bracket tags
3. **workflow-reference** -- Verification of attack model consistency

### Path C: Understanding the Tooling

1. **ivy-toolkit** -- Architecture (LSP + MCP + native), consolidated tools, coordination workflows
2. **lsp-patterns** -- LSP invocation patterns, scoped-access policy
3. **ivy-lsp-walkthrough** -- Concrete end-to-end example
4. **workflow-reference** -- Verify-debug-fix cycle

### Path D: Incremental Specification Development

1. **ivy-writing-guide** -- Ivy syntax basics
2. **specification-patterns** -- 14-layer template
3. **incremental-spec-dev** -- Add-verify-iterate loop
4. **counterexample-guide** -- When verification fails

## Skill Details

### ivy-workflow-orchestrator
- **Category**: Orchestration & Tooling
- **Purpose**: Central 5-phase engine (Explore → Plan → Write → Verify → Finalize) with iron laws — enforces exploration-first, plan-before-write, verify-before-compile discipline for all Ivy specification work.
- **Related skills**: ivy-toolkit, specification-patterns, workflow-reference, ivy-writing-guide, incremental-spec-dev

### ivy-toolkit
- **Category**: Orchestration & Tooling
- **Purpose**: Single source of truth for all ivy-tools MCP tool documentation and tool selection guidance. Supersedes duplicated tool sections in other skills.
- **Related skills**: tooling-reference (architecture overview)

### methodology-reference
- **Category**: Methodology
- **Purpose**: Comprehensive reference for all three PANTHER methodologies (NCT, NACT, NSCT) with full workflows, red flags, common mistakes, and directory structures. Links to dedicated sub-skills for deep dives.
- **Related commands**: `/nct-check`, `/nct-compile`, `/nct-scaffold`, `/nct-review`

### nct-methodology
- **Category**: Methodology
- **Purpose**: NCT (Network-Centric Compositional Testing): specification-based protocol compliance testing. Covers the 10-step NCT workflow, role inversion, test traffic generation, directory structure, and common mistakes.
- **Related commands**: `/nct-check`, `/nct-compile`, `/nct-scaffold`

### nact-methodology
- **Category**: Methodology
- **Purpose**: NACT (Network-Attack Compositional Testing): security testing using the APT 6-stage lifecycle. Covers attack entities, protocol-specific bindings, threat model definition, and adversarial monitors.
- **Prerequisites**: nct-methodology

### nsct-methodology
- **Category**: Methodology
- **Purpose**: NSCT (Network-Simulator Centric Compositional Testing): large-scale simulation testing with Shadow Network Simulator. Covers deterministic execution, topology control, and Shadow NS configuration.
- **Prerequisites**: nct-methodology

### specification-patterns
- **Category**: Specification Writing
- **Purpose**: 14-layer structural template for protocol decomposition plus the formal model pattern library (variants, serdes, shims, monitors, entities, modules). Includes dependency graphs, minimal viable sets, scaffolding order, and composition rules.
- **Related commands**: `/nct-scaffold`, `/nct-add-pattern`

### ivy-writing-guide
- **Category**: Specification Writing
- **Purpose**: Ivy language syntax reference, test specification patterns (includes, exports, before/after, `_finalize`), and RFC bracket-tag annotation guide for traceability.

### incremental-spec-dev
- **Category**: Specification Writing
- **Purpose**: Guides the add-verify-iterate loop for adding RFC requirements one at a time with verification between each addition.
- **Prerequisites**: ivy-writing-guide, specification-patterns

### counterexample-guide
- **Category**: Specification Writing
- **Purpose**: Systematic workflow for reading counterexample traces from ivy_verify, diagnosing root causes, and applying fixes.
- **Prerequisites**: ivy-writing-guide

### lsp-patterns
- **Category**: Tooling
- **Purpose**: LSP invocation patterns permitted in validation and health-check contexts. Reference for when and how to call LSP tools (hover, goToDefinition, findReferences, documentSymbol) within the scoped-access policy.

### ivy-lsp-walkthrough
- **Category**: Tooling
- **Purpose**: End-to-end walkthrough: adding rfc9000:7.3 to the QUIC spec using LSP for navigation and MCP for analysis/verification.
- **Prerequisites**: ivy-toolkit, lsp-patterns

### workflow-reference
- **Category**: Workflow
- **Purpose**: RFC-to-Ivy mapping patterns, verification workflows, quality gate pipeline, and debugging strategies.

### interaction-patterns
- **Category**: Interaction
- **Purpose**: Reusable checkpoint types (Gate, Inform-and-Continue, Collaborative), question formats, and adaptive follow-up rules for consistent user interaction across all agents.

### claim-discussion
- **Category**: Interaction
- **Purpose**: Structured decision trees for verification claim resolution, RFC requirement mapping, and coverage gap prioritization.
- **Prerequisites**: interaction-patterns, counterexample-guide

### adaptive-interview
- **Category**: Interaction
- **Purpose**: Navigator agent's interview logic: context detection, goal identification, methodology selection, target scoping, and dispatch to specialist agents.

### healthcheck
- **Category**: Utility
- **Purpose**: Fast triage checklist for the Ivy MCP sidecar and LSP stack. Checks port/PID files, SSE connection state, indexer readiness, and process lifecycle. Use before any MCP tool call when the server appears unresponsive.

### ivy-protocol-model-builder
- **Category**: Process
- **Purpose**: Interactive 6-phase workflow for creating new formal Ivy protocol specifications from scratch. Covers RFC requirement extraction, 14-layer template scaffolding, incremental verification, and coverage gating.

### propagation-patterns
- **Category**: Reference
- **Purpose**: Patterns for propagating type changes across serializer/deserializer state machines. Covers dependency-ordered update sequences, variant type propagation, and re-verification checkpoints.

### workspace-management
- **Category**: Utility
- **Purpose**: Set, clear, and auto-detect the active Ivy protocol workspace. Covers the `ivy_workspace` MCP tool, `.ivyworkspace` markers, write-isolation semantics, and workspace restore on session start.

## Skills vs Agents vs Commands

| Concept | Purpose | Invocation | Interaction |
|---------|---------|------------|-------------|
| **Skill** | Provides reference material and domain knowledge; surfaced automatically when trigger patterns match | Automatic (Claude Code matches user query to skill `description` frontmatter) | Passive -- informs the LLM's response with knowledge |
| **Agent** | Executes a multi-step interactive workflow using MCP tools and user input | `@agent-name` or selected by Claude Code when a task matches | Active -- calls tools, asks questions, produces artifacts |
| **Command** | Runs a single focused operation (verify, compile, scaffold) | `/command-name [args]` | Active -- executes one action and returns results |

### Available Agents (5)

| Agent | Purpose |
|-------|---------|
| navigator | Adaptive entry point — detects user expertise, goals, and context to route to the right agent or workflow |
| model-reviewer | Reviews Ivy model files for quality, correctness, and best practices |
| methodology-guide | Interactive guide for NCT, NACT, and NSCT methodologies |
| spec-analyst | Navigates, explores, verifies, and diagnoses Ivy protocol specifications |
| traceability-agent | Extracts RFC requirements, creates manifests, and audits coverage |

### Available Commands (9)

| Command | Purpose |
|---------|---------|
| `/nct-add-pattern` | Add a formal model pattern to an existing protocol specification |
| `/nct-check` | Run formal verification (`ivy_check`) on an Ivy file |
| `/nct-compile` | Compile an Ivy file to a test executable (`ivyc`) |
| `/nct-model-info` | Display model structure (`ivy_show`) |
| `/nct-scaffold` | Scaffold a new protocol model or test specification |
| `/nct-health` | Run health check for Ivy LSP + MCP integration |
| `/nct-review` | Comprehensive multi-agent specification review |
| `/nct-validate` | Comprehensive correctness validation with full raw-output report |
| `/nct-observability` | Query and analyze Ivy observability session logs |
