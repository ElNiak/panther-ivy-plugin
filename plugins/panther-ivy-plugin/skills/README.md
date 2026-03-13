# Skills

## Overview

- 12 skills providing domain knowledge for Ivy protocol testing within the PANTHER framework
- Skills are surfaced automatically by Claude Code when trigger patterns in the user's query match a skill's `description` frontmatter
- They provide **reference material** (language guides, workflow steps, tool catalogs); agents and commands provide interactive workflows and execution

## Skill Catalog

### Methodology

| Skill | Description | Trigger Keywords |
|-------|-------------|------------------|
| [nct-methodology](nct-methodology/) | Step-by-step NCT (Network-Centric Compositional Testing) workflow for specification-based testing where a formal Ivy model plays one role against an IUT | "compositional testing", "protocol specification", "formal verification", "NCT", "specification-based testing", "role-based testing", "test against IUT", "Ivy protocol testing" |
| [nact-methodology](nact-methodology/) | NACT (Network-Attack Compositional Testing) methodology extending NCT with the APT 6-stage lifecycle to model and test protocols from an attacker's perspective | "attack testing", "APT", "threat modeling", "security verification", "NACT", "attack lifecycle", "attacker specification", "security testing with Ivy", "penetration testing formal model" |
| [nsct-methodology](nsct-methodology/) | NSCT (Network-Simulator Centric Compositional Testing) methodology for running protocol verification in simulated network environments using Shadow Network Simulator | "simulation", "Shadow NS", "Shadow Network Simulator", "network simulator", "NSCT", "simulation-based testing", "network topology testing", "large-scale testing", "deterministic testing" |

### Specification Writing

| Skill | Description | Trigger Keywords |
|-------|-------------|------------------|
| [14-layer-template](14-layer-template/) | Structural template for decomposing any network protocol into 14 modular Ivy specification layers, organized into Core Protocol Stack, Entity Model, Infrastructure, and Optional Layers | "creating a new protocol model", "protocol specification architecture", "layer architecture", "14-layer template", "formal model structure", "protocol decomposition", "scaffolding a protocol", "Ivy model layers" |
| [ivy-model-editing](ivy-model-editing/) | Ivy language reference covering syntax, declaration types (type, relation, action, object, module, instance, isolate), module system, and protocol modeling best practices | "editing Ivy formal specification files", "Ivy syntax", "declaration types", "module system", "protocol modeling" |
| [writing-test-specs](writing-test-specs/) | Guide for writing Ivy test specifications: structure, includes, initialization, exported actions, before/after clauses, `_finalize`, test variants, and weight attributes | "writing test files", "test specifications", "monitors", "assertions", "before/after clauses", "_finalize", "export actions", "test variants", "writing Ivy tests", "creating protocol tests" |
| [annotated-spec-writing](annotated-spec-writing/) | How to add RFC bracket-tag annotations (`[rfc9000:4.1]`) to Ivy assertions for automated traceability, coverage tracking, and gap analysis through the Ivy LSP | "writing annotated specs", "bracket tags", "RFC traceability annotations", "tagged assertions", "requirement coverage", "annotating Ivy files" |

### RFC Mapping

| Skill | Description | Trigger Keywords |
|-------|-------------|------------------|
| [rfc-to-ivy-mapping](rfc-to-ivy-mapping/) | Systematic approach to translating RFC normative language (MUST/SHOULD/MAY) into formal Ivy constructs (require, invariant, before/after monitors) with mapping patterns and examples | "translating RFC", "requirements extraction", "specification mapping", "RFC to Ivy", "mapping MUST SHOULD MAY", "formalizing RFC requirements", "extracting protocol requirements" |

### Tooling

| Skill | Description | Trigger Keywords |
|-------|-------------|------------------|
| [ivy-tools-reference](ivy-tools-reference/) | Tool catalog for the ivy-tools MCP server (read-only diagnostics): ivy_verify, ivy_compile, ivy_model_info, ivy_lint, ivy_include_graph, ivy_capabilities, ivy_traceability_matrix, ivy_requirement_coverage, ivy_impact_analysis, ivy_extract_requirements, ivy_cross_references, ivy_query_symbol | "ivy diagnostics", "ivy lint", "ivy verification", "ivy coverage", "ivy traceability", "ivy include graph", "ivy capabilities", "ivy impact analysis", "ivy requirements", "ivy cross references", "ivy query symbol" |
| [ivy-tooling-guide](ivy-tooling-guide/) | Ivy tooling architecture guide: native LSP (diagnostics, go-to-definition, find-references, hover), ivy-tools MCP (verification, compilation, analysis), and Claude's native tools (Read, Edit, Write, Grep, Glob) | "Ivy tool guidance", "tooling architecture", "code navigation", "MCP tools for Ivy", "LSP for Ivy", "ivy-tools" |

### Workflow

| Skill | Description | Trigger Keywords |
|-------|-------------|------------------|
| [ivy-verification](ivy-verification/) | End-to-end verification workflow: running ivy_check via MCP, interpreting success/failure output, debugging invariant violations, type safety errors, counterexample traces, and Z3 timeouts | "running formal verification", "ivy_check workflow", "verifying protocol specifications", "debugging verification failures", "interpreting ivy_check output", "invariant violations", "type safety errors", "verification debugging" |
| [quality-gate-reference](quality-gate-reference/) | Multi-gate quality evaluation pipeline: scoring system, self-repair loop, quality dimensions for write and read agents, hook architecture | "quality gates", "quality evaluation", "quality scoring", "self-repair loop", "quality dimensions", "agent output quality" |

## Learning Paths

### Path A: New to Ivy Protocol Testing

For someone unfamiliar with the PANTHER Ivy workflow who wants to build their first protocol model.

1. **nct-methodology** -- Understand the overall NCT approach: role inversion, specification structure, the 10-step workflow
2. **14-layer-template** -- Learn how to decompose a protocol into 14 modular layers and which are required
3. **ivy-model-editing** -- Master Ivy language syntax: types, relations, actions, objects, modules, isolates
4. **writing-test-specs** -- Write test specifications with includes, exports, before/after clauses, and `_finalize`
5. **ivy-verification** -- Run formal verification, interpret errors, and debug failures

### Path B: Security Testing with NACT

For someone who already understands NCT and wants to add adversarial testing.

1. **nact-methodology** -- Learn the APT 6-stage lifecycle and attack entity roles (attacker, bot, C2, MIM)
2. **rfc-to-ivy-mapping** -- Map security-relevant RFC requirements (MUST NOT, error handling) to Ivy assertions
3. **annotated-spec-writing** -- Add RFC bracket tags for traceability of security properties
4. **ivy-verification** -- Verify attack model consistency before compiling attack tests

### Path C: Understanding the Tooling

For someone who wants to use the MCP tool ecosystem effectively.

1. **ivy-tooling-guide** -- Understand the tooling architecture (native LSP + ivy-tools MCP + Claude's native tools) and why direct CLI is blocked
2. **ivy-tools-reference** -- Learn the 12 read-only diagnostic tools: verification, linting, coverage, traceability, dependency graphs, impact analysis
3. **ivy-verification** -- Apply the tools in a verify-debug-fix cycle

## Skill Details

### 14-layer-template

- **Category**: Specification Writing
- **Purpose**: Provides the structural blueprint for decomposing any network protocol into modular Ivy specifications. Defines all 14 layers (Types, Application, Security/Handshake, Frame/Message, Packet, Protection, Connection/State, Transport Parameters, Error Handling, Entity Definitions, Entity Behavior, Shims, Serialization, Utilities) plus optional layers. Includes a dependency graph, minimal viable set, and a decision matrix for template selection based on protocol properties.
- **Trigger keywords**: "creating a new protocol model", "protocol specification architecture", "layer architecture", "14-layer template", "formal model structure", "protocol decomposition", "scaffolding a protocol", "Ivy model layers"
- **Key topics**: 14-layer decomposition, layer dependency graph, Core Protocol Stack (layers 1-9), Entity Model (layers 10-12), Infrastructure (layers 13-14), optional layers (TLS/DTLS, FSM, recovery, attacks), directory structure per protocol, minimal viable set, scaffolding a new protocol, reusable components
- **Related agents**: nct-guide, nact-guide
- **Related commands**: `/nct-new-protocol`

### annotated-spec-writing

- **Category**: Specification Writing
- **Purpose**: Explains how to link formal Ivy assertions to RFC requirements using bracket tag comments for automated traceability, coverage tracking, and gap analysis. Covers tag syntax, ID conventions, requirement manifests, and LSP diagnostic integration.
- **Trigger keywords**: "writing annotated specs", "bracket tags", "RFC traceability annotations", "tagged assertions", "requirement coverage", "annotating Ivy files"
- **Key topics**: Bracket tag syntax (`[rfc9000:4.1]`), tag ID conventions, requirement manifests (`*_requirements.yaml`), coverage statistics by level (MUST/SHOULD/MAY) and by layer, orphaned tag detection, LSP diagnostics (hints, warnings, code lens)
- **Related agents**: traceability-reviewer, requirement-extractor
- **Related skills**: rfc-to-ivy-mapping, ivy-tools-reference

### ivy-model-editing

- **Category**: Specification Writing
- **Purpose**: Comprehensive Ivy language reference for editing formal specification files. Covers all declaration types, the object and module system, protocol modeling patterns, include directives, and common pitfalls.
- **Trigger keywords**: "editing Ivy formal specification files", "Ivy syntax", "declaration types", "module system", "protocol modeling"
- **Key topics**: `#lang ivy1.7` pragma, type declarations (uninterpreted, enumerated, built-in), relations, functions, individuals, actions (require/ensure), invariants, axioms, conjectures, objects (`type this`, nesting), modules (parameterized), instances, isolates, protocol modeling patterns (client/server roles, state machines, packet types), include directives, common pitfalls (missing `after init`, ungrounded variables, circular includes)
- **Related agents**: ivy-model-reviewer, spec-explorer
- **Related skills**: 14-layer-template, writing-test-specs

### ivy-tools-reference

- **Category**: Tooling
- **Purpose**: Complete tool catalog for the ivy-tools MCP server. Documents all 12 read-only diagnostic and analysis tools with parameters, return types, and recommended workflows.
- **Trigger keywords**: "ivy diagnostics", "ivy lint", "ivy verification", "ivy coverage", "ivy traceability", "ivy include graph", "ivy capabilities", "ivy impact analysis", "ivy requirements", "ivy cross references", "ivy query symbol"
- **Key topics**: ivy_verify (formal verification), ivy_compile (test compilation), ivy_model_info (model introspection), ivy_lint (fast structural lint), ivy_include_graph (dependency graph), ivy_capabilities (tool availability), ivy_traceability_matrix (RFC coverage), ivy_requirement_coverage (coverage stats), ivy_impact_analysis (symbol edges), ivy_extract_requirements (RFC parsing), ivy_cross_references (graph neighborhood), ivy_query_symbol (rich symbol info)
- **Related agents**: spec-verifier, traceability-reviewer
- **Related skills**: ivy-tooling-guide, ivy-verification

### ivy-verification

- **Category**: Workflow
- **Purpose**: End-to-end verification workflow using ivy-tools MCP and native Ivy LSP. Covers running `ivy_check`, interpreting success/failure, common error patterns (invariant not preserved, type safety, ungrounded relations, Z3 timeouts), and a systematic debugging cycle.
- **Trigger keywords**: "running formal verification", "ivy_check workflow", "verifying protocol specifications", "debugging verification failures", "interpreting ivy_check output", "invariant violations", "type safety errors", "verification debugging"
- **Key topics**: Running verification via MCP, interpreting OK/failure output, counterexample traces, invariant preservation failures, type safety errors, ungrounded relations, safety property violations, circular dependencies, Z3 timeout handling, debugging cycle (check -> read error -> locate -> diagnose -> fix -> re-check)
- **Related agents**: spec-verifier, ivy-model-reviewer
- **Related commands**: `/nct-check`, `/nct-compile`, `/nct-model-info`

### nact-methodology

- **Category**: Methodology
- **Purpose**: Describes NACT (Network-Attack Compositional Testing), which extends NCT to model and test protocols from an attacker's perspective using the APT (Advanced Persistent Threat) 6-stage lifecycle: Reconnaissance, Infiltration, C2 Communication, Privilege Escalation, Persistence, Exfiltration plus White Noise.
- **Trigger keywords**: "attack testing", "APT", "threat modeling", "security verification", "NACT", "attack lifecycle", "attacker specification", "security testing with Ivy", "penetration testing formal model"
- **Key topics**: APT 6-stage lifecycle (3 phases: Infiltration, Expansion, Extraction), attack entities (Attacker, Bot, C2 Server, Target, MIM), protocol-specific bindings (QUIC, MiniP, UDP), lifecycle composition via `attack_life_cycle.ivy`, apt directory structure, NACT 9-step workflow, relationship to NCT
- **Related agents**: nact-guide
- **Related skills**: nct-methodology, rfc-to-ivy-mapping

### nct-methodology

- **Category**: Methodology
- **Purpose**: Core NCT (Network-Centric Compositional Testing) methodology where a formal Ivy protocol specification plays one role against an Implementation Under Test. Covers role inversion, specification structure (before/after monitors, `_finalize`), test traffic generation via Z3/SMT, and a 10-step workflow from RFC to executable test.
- **Trigger keywords**: "compositional testing", "protocol specification", "formal verification", "NCT", "specification-based testing", "role-based testing", "test against IUT", "Ivy protocol testing"
- **Key topics**: Role inversion (testing server = Ivy acts as client), before/after monitors, `_finalize` end-state verification, exported actions for test mirror generation, Z3/SMT symbolic execution, 10-step NCT workflow, directory structure, QUIC reference example (50+ test variants)
- **Related agents**: nct-guide, spec-explorer
- **Related commands**: `/nct-check`, `/nct-compile`, `/nct-new-protocol`, `/nct-new-test`

### nsct-methodology

- **Category**: Methodology
- **Purpose**: NSCT (Network-Simulator Centric Compositional Testing) methodology for running protocol verification in simulated network environments using Shadow Network Simulator. Enables deterministic execution, complex topologies, and controlled network conditions.
- **Trigger keywords**: "simulation", "Shadow NS", "Shadow Network Simulator", "network simulator", "NSCT", "simulation-based testing", "network topology testing", "large-scale testing", "deterministic testing"
- **Key topics**: Shadow NS integration, deterministic execution (seed-based replay), scale testing, topology control (latency, loss, bandwidth, jitter), NCT vs NSCT comparison matrix, PANTHER experiment config with `type: shadow_ns`, Shadow NS build mode (`build_mode: ""`), comprehensive testing strategy (NCT first, NACT second, NSCT third)
- **Related agents**: nsct-guide
- **Related skills**: nct-methodology, nact-methodology

### ivy-tooling-guide

- **Category**: Tooling
- **Purpose**: Explains the tooling architecture (native Ivy LSP for language intelligence, ivy-tools MCP for verification and analysis, Claude's native tools for code navigation and editing) and provides a complete tool mapping from CLI commands to their MCP/LSP/native equivalents. Documents the enforcement hook that blocks direct CLI usage.
- **Trigger keywords**: "Ivy tool guidance", "tooling architecture", "how to check Ivy files", "how to compile Ivy", "formal verification tools", "ivy_check alternative", "MCP tools for Ivy", "LSP for Ivy"
- **Key topics**: Tooling architecture (LSP + MCP + native tools), CLI-to-tool mapping, native Ivy LSP features (diagnostics, go-to-definition, find-references, hover), Claude's native tools (Read, Edit, Write, Grep, Glob), ivy-tools MCP (verification, compilation, analysis), Navigate -> Understand -> Edit -> Verify workflow, PreToolUse enforcement hook
- **Related agents**: spec-explorer, ivy-model-reviewer
- **Related skills**: ivy-tools-reference, ivy-verification

### rfc-to-ivy-mapping

- **Category**: RFC Mapping
- **Purpose**: Systematic approach to translating RFC normative language (MUST/SHOULD/MAY per RFC 2119) into formal Ivy constructs. Provides concrete mapping patterns (MUST to `require`, state transitions to `before` guards, counting to `after` updates, end-state to `_finalize`) with QUIC examples.
- **Trigger keywords**: "translating RFC", "requirements extraction", "specification mapping", "RFC to Ivy", "mapping MUST SHOULD MAY", "formalizing RFC requirements", "extracting protocol requirements"
- **Key topics**: RFC 2119 normative keywords, MUST/MUST NOT/SHOULD/MAY mapping to Ivy constructs, mapping patterns (require, before/after, invariant, _finalize), Ivy constructs reference table, systematic 5-step mapping workflow, common pitfalls (ambiguous language, untestable requirements, circular dependencies)
- **Related agents**: requirement-extractor, traceability-reviewer
- **Related skills**: annotated-spec-writing, nct-methodology, writing-test-specs

### quality-gate-reference

- **Category**: Workflow
- **Purpose**: Documents the multi-gate quality evaluation pipeline that automatically evaluates all agent outputs. Covers scoring system (structural, type safety, semantic, traceability for write agents; accuracy, completeness, tool usage for read agents), self-repair loop via SubagentStop hooks, and the quality-gate agent for manual audits.
- **Trigger keywords**: "quality gates", "quality evaluation", "quality scoring", "self-repair loop", "quality dimensions", "agent output quality"
- **Key topics**: 3-gate architecture (PostToolUse lint, SubagentStop agent hook for write agents, SubagentStop prompt hook for read agents), scoring weights, PASS/FAIL thresholds, self-repair mechanism (1 retry via stop_hook_active), quality-gate agent for on-demand evaluation
- **Related agents**: quality-gate, ivy-model-reviewer
- **Related skills**: ivy-tools-reference, ivy-verification

### writing-test-specs

- **Category**: Specification Writing
- **Purpose**: Practical guide for writing Ivy test specification files. Covers the full structure (includes, initialization, exports, before/after clauses, `_finalize`), role isolation (server tests, client tests, MIM tests), test variants with weight attributes, and a checklist for complete test files.
- **Trigger keywords**: "writing test files", "test specifications", "monitors", "assertions", "before/after clauses", "_finalize", "export actions", "test variants", "writing Ivy tests", "creating protocol tests"
- **Key topics**: Test specification structure (6 sections), includes ordering, `after init` setup (sockets, TLS, transport parameters), exported actions for test mirror, before/after clauses in behavior files, `_finalize` end-state verification, role isolation (server/client/MIM tests), test variants, weight attributes for biased generation, common variant patterns (stream, connection_close, retry, migration, 0rtt, timeout, error)
- **Related agents**: nct-guide, spec-verifier
- **Related commands**: `/nct-new-test`, `/nct-check`, `/nct-compile`

## Skills vs Agents vs Commands

| Concept | Purpose | Invocation | Interaction |
|---------|---------|------------|-------------|
| **Skill** | Provides reference material and domain knowledge; surfaced automatically when trigger patterns match | Automatic (Claude Code matches user query to skill `description` frontmatter) | Passive -- informs the LLM's response with knowledge |
| **Agent** | Executes a multi-step interactive workflow using MCP tools and user input | `@agent-name` or selected by Claude Code when a task matches | Active -- calls tools, asks questions, produces artifacts |
| **Command** | Runs a single focused operation (verify, compile, scaffold) | `/command-name [args]` | Active -- executes one action and returns results |

### Available Agents (8)

| Agent | Purpose |
|-------|---------|
| ivy-model-reviewer | Reviews Ivy model files for quality, correctness, and best practices |
| nct-guide | Interactive NCT workflow guide |
| nact-guide | Interactive NACT workflow guide |
| nsct-guide | Interactive NSCT workflow guide |
| requirement-extractor | Extracts RFC normative requirements and generates manifests |
| spec-explorer | Navigates and explains Ivy protocol specification structure |
| spec-verifier | Runs verification and helps debug failures |
| traceability-reviewer | Audits RFC coverage and bracket-tag annotations |

### Available Commands (5)

| Command | Purpose |
|---------|---------|
| `/nct-check` | Run formal verification (`ivy_check`) on an Ivy file |
| `/nct-compile` | Compile an Ivy file to a test executable (`ivyc`) |
| `/nct-model-info` | Display model structure (`ivy_show`) |
| `/nct-new-protocol` | Scaffold a new protocol model from the 14-layer template |
| `/nct-new-test` | Create a new test specification file |
