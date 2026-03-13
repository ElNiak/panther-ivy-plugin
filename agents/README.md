# Agents

## Overview

This directory contains 9 specialized Claude Code agents for Ivy protocol testing tasks within the PANTHER framework. Each agent is defined as a Markdown file with YAML frontmatter specifying its name, description, example triggers, available tools, and color.

Agents are invoked automatically when the user's request matches a trigger pattern described in the frontmatter `description` field, or explicitly by referencing the agent name.

## Agent Selection Guide

| Task | Agent | Methodology |
|------|-------|-------------|
| Navigate specs, explore dependencies, onboard to a protocol model | `spec-explorer` | All |
| Create a new formal specification, test IUT compliance | `nct-guide` | NCT |
| Attack testing, threat modeling, APT lifecycle, attacker entities | `nact-guide` | NACT |
| Simulation-based testing, Shadow NS, large-scale / deterministic tests | `nsct-guide` | NSCT |
| Verify or compile Ivy specs, diagnose failures | `spec-verifier` | All |
| Review Ivy model quality, pre-commit validation | `ivy-model-reviewer` | All |
| Extract RFC requirements, generate requirement manifests | `requirement-extractor` | All |
| Audit RFC coverage, traceability gap analysis | `traceability-reviewer` | All |
| Comprehensive quality evaluation, scoring, pre-commit audit | `quality-gate` | All |

## Agent Details

### spec-explorer

**Purpose:** Specification navigator and explainer for Ivy formal protocol models. Helps users understand existing specifications -- navigate, explain, and map the codebase.

**When to use:**
- Onboarding to an existing protocol model (e.g., "Walk me through the QUIC protocol specification structure")
- Finding which tests exercise specific protocol features (e.g., "Which tests exercise QUIC connection migration?")
- Tracing include dependencies between .ivy files (e.g., "What does quic_packet.ivy include and what includes it?")
- Exploring layer relationships and directory structure

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `ToolSearch`

**Example prompts:**
- "Walk me through the QUIC protocol specification structure"
- "Which tests exercise QUIC connection migration?"
- "What does quic_packet.ivy include and what includes it?"

---

### nct-guide

**Purpose:** Expert guide for the Network-Centric Compositional Testing (NCT) methodology. Walks users through protocol decomposition, specification writing, verification, compilation, and testing against an IUT.

**When to use:**
- Creating a new formal specification for a protocol (e.g., "I need to write an Ivy specification for the CoAP protocol")
- Testing an IUT against a formal spec (e.g., "How do I test the picoquic server against my QUIC spec?")
- Writing before/after monitors that encode RFC requirements (e.g., "I need to add a requirement that the server must echo the nonce in its response")
- Working through the 14-layer formal model template

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

**Example prompts:**
- "I need to write an Ivy specification for the CoAP protocol"
- "How do I test the picoquic server against my QUIC spec?"
- "I need to add a requirement that the server must echo the nonce in its response"

---

### nact-guide

**Purpose:** Expert guide for the Network-Attack Compositional Testing (NACT) methodology. Covers threat modeling, attack entity design, attacker specification writing, and the APT (Advanced Persistent Threat) 6-stage lifecycle model.

**When to use:**
- Modeling attacks against protocol implementations (e.g., "I want to test QUIC server resilience against reconnaissance and infiltration attacks")
- Designing attacker entities in Ivy (e.g., "How do I create a man-in-the-middle attacker entity in Ivy?")
- Creating protocol-specific APT lifecycle bindings (e.g., "I need to create attack bindings for my BGP protocol model")
- Security property verification (confidentiality, integrity, availability)

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

**Example prompts:**
- "I want to test QUIC server resilience against reconnaissance and infiltration attacks"
- "How do I create a man-in-the-middle attacker entity in Ivy?"
- "I need to create attack bindings for my BGP protocol model"

---

### nsct-guide

**Purpose:** Expert guide for the Network-Simulator Centric Compositional Testing (NSCT) methodology. Helps configure Shadow Network Simulator for deterministic, large-scale, topology-controlled protocol testing.

**When to use:**
- Testing protocol behavior at scale with many nodes (e.g., "I need to test how my QUIC implementation behaves with 50 simultaneous clients")
- Deterministic, reproducible test execution (e.g., "My test fails intermittently. I need deterministic reproduction of the failure.")
- Testing under specific network conditions (e.g., "How does the protocol behave with 200ms latency and 5% packet loss?")
- Comparing NCT vs NSCT tradeoffs

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

**Example prompts:**
- "I need to test how my QUIC implementation behaves with 50 simultaneous clients"
- "My test fails intermittently. I need deterministic reproduction of the failure."
- "How does the protocol behave with 200ms latency and 5% packet loss?"

---

### spec-verifier

**Purpose:** Verification and diagnosis specialist for Ivy formal protocol specifications. Runs formal checks, interprets results, and suggests fixes. This is a workflow agent -- it executes checks and reports structured PASS/FAIL results, not a methodology teacher.

**When to use:**
- Verifying Ivy specs for invariant violations (e.g., "Can you verify my QUIC connection spec for any invariant violations?")
- Diagnosing compilation errors (e.g., "I'm getting 'isolate assumption failed' when compiling quic_server_test_stream.ivy")
- Inspecting model structure before testing (e.g., "Show me the types and actions in my protocol model")
- Cross-referencing failures with spec structure

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

**Example prompts:**
- "Can you verify my QUIC connection spec for any invariant violations?"
- "I'm getting 'isolate assumption failed' when compiling quic_server_test_stream.ivy"
- "Show me the types and actions in my protocol model"

---

### ivy-model-reviewer

**Purpose:** Expert reviewer of Ivy formal specification models. Analyzes `.ivy` files for correctness, completeness, and adherence to best practices. Reports findings organized by severity (ERROR / WARNING / INFO). Read-only -- does not modify files.

**When to use:**
- Quality review of Ivy models (e.g., "Review my QUIC frame specification for any issues")
- Checking invariant quality and modeling concerns (e.g., "Can you check if my protocol model has any invariant problems?")
- Pre-commit validation of `.ivy` changes (e.g., "I'm about to commit these Ivy changes. Anything wrong with the model?")
- Detecting anti-patterns: unguarded `assume`, missing invariants, deeply nested quantifiers

**Tools available:** `Read`, `Grep`, `Glob`, `ToolSearch`

**Example prompts:**
- "Review my QUIC frame specification for any issues"
- "Can you check if my protocol model has any invariant problems?"
- "I'm about to commit these Ivy changes. Anything wrong with the model?"

---

### requirement-extractor

**Purpose:** RFC requirement extraction specialist. Parses RFC text, identifies normative requirements (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY per RFC 2119), and produces structured YAML requirement manifests that the Ivy LSP can consume for traceability.

**When to use:**
- Extracting normative requirements from RFC text (e.g., "Extract all MUST and SHOULD requirements from RFC 9000 section 4")
- Creating or seeding `*_requirements.yaml` manifest files (e.g., "Create a requirements manifest for the QUIC connection layer")
- Updating existing manifests with newly discovered requirements (e.g., "I found more requirements in section 8.1, add them to the manifest")
- Normalizing requirement levels (SHALL -> MUST, RECOMMENDED -> SHOULD, OPTIONAL -> MAY)

**Tools available:** `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`

**Example prompts:**
- "Extract all MUST and SHOULD requirements from RFC 9000 section 4"
- "Create a requirements manifest for the QUIC connection layer"
- "I found more requirements in section 8.1, add them to the manifest"

---

### traceability-reviewer

**Purpose:** RFC traceability review specialist. Analyzes the mapping between RFC requirements (from YAML manifests) and Ivy assertions (bracket tags in `.ivy` files), identifies coverage gaps, and produces prioritized review reports.

**When to use:**
- Identifying uncovered RFC requirements (e.g., "Which MUST requirements from RFC 9000 are we missing?")
- Running full traceability audits (e.g., "Run a full traceability review of our QUIC protocol specs")
- Tracking incremental coverage improvements (e.g., "Did the new stream tests improve our RFC coverage?")
- Finding orphaned tags, untagged assertions, and duplicate coverage

**Tools available:** `Bash`, `Read`, `Glob`, `Grep`, `WebFetch`

**Example prompts:**
- "Which MUST requirements from RFC 9000 are we missing?"
- "Run a full traceability review of our QUIC protocol specs"
- "Did the new stream tests improve our RFC coverage?"

### quality-gate

**Purpose:** Comprehensive quality evaluation agent for Ivy specifications and requirement manifests. Runs a 4-gate pipeline (structural → type safety → semantic → traceability) and produces scored quality reports. Also invoked automatically via SubagentStop hooks to evaluate write and read agent outputs.

**When to use:**
- Quality audit of Ivy specifications (e.g., "Run a quality check on my CoAP specification")
- Pre-commit validation (e.g., "Quality check everything in protocol-testing/quic/quic_stack/")
- Evaluating requirement manifest quality (e.g., "Check the quality of my RFC 9000 requirements manifest")

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `ToolSearch`

**Example prompts:**
- "Run a quality check on my new CoAP specification"
- "Quality check everything in protocol-testing/quic/quic_stack/"
- "Check the quality of my RFC 9000 requirements manifest"

---

## Agent Relationships

**Methodology agents** provide end-to-end workflow structure for their respective testing paradigms:
- `nct-guide` -- Network-Centric Compositional Testing (formal spec compliance)
- `nact-guide` -- Network-Attack Compositional Testing (security and threat modeling)
- `nsct-guide` -- Network-Simulator Centric Compositional Testing (scale and determinism)

NCT and NACT are complementary: NCT verifies correctness, NACT verifies security. Both use the same Ivy language and before/after monitor pattern. NACT adds attack entity roles and the APT lifecycle framework on top of protocol specs from NCT. NSCT reuses the same Ivy formal specifications but changes the execution environment from real Docker networks to simulated Shadow NS networks.

**Utility agents** provide focused capabilities usable across all methodologies:
- `spec-explorer` -- Navigate and understand existing specifications
- `spec-verifier` -- Verify and compile specifications, diagnose failures
- `ivy-model-reviewer` -- Review model quality before committing changes
- `requirement-extractor` + `traceability-reviewer` -- These two form a pair: the extractor produces `*_requirements.yaml` manifests from RFC text, and the traceability reviewer audits how well the Ivy assertions cover those requirements.
- `quality-gate` -- Comprehensive quality evaluation across all dimensions (structural, type safety, semantic, traceability). Also invoked automatically via SubagentStop hooks to evaluate other agents' outputs.

## MCP Tool Enforcement

All agents use two tool sources:
- **Claude's native tools + Ivy LSP** -- Code navigation (`Read`, `Grep`, `Glob`, `Edit`, `Write`) and Ivy-specific LSP features (diagnostics, go-to-definition, find-references, hover) configured via `.lsp.json`
- **ivy-tools MCP** -- Ivy verification (`ivy_verify`, `ivy_compile`, `ivy_model_info`), linting (`ivy_lint`), requirement extraction (`ivy_extract_requirements`), traceability (`ivy_traceability_matrix`, `ivy_requirement_coverage`), and analysis tools (`ivy_impact_analysis`, `ivy_cross_references`, `ivy_query_symbol`) configured via `.mcp.json`

**Available Protocol Models:**
- **QUIC** (complete, 202+ files) — `protocol-testing/quic/`
- **BGP** (partial) — `protocol-testing/bgp/`
- **CoAP** (partial) — `protocol-testing/coap/`
- **HTTP** (minimal) — `protocol-testing/http/`
- **MiniP** (partial, flat structure) — `protocol-testing/minip/`
- **System** (system-level specs: entities, network, protocols) — `protocol-testing/system/`
- **new_prot** (template, empty files) — `protocol-testing/new_prot/`
- **APT** (cross-cutting attacks) — `protocol-testing/apt/`

A `PreToolUse` hook (`hooks/scripts/block-direct-ivy.sh`) intercepts all `Bash` tool calls and blocks direct invocations of `ivy_check`, `ivyc`, `ivy_show`, and `ivy_to_cpp`. If a blocked command is detected, the hook exits with a message directing the user to the corresponding MCP tool:

| Blocked CLI command | Required MCP tool |
|---------------------|-------------------|
| `ivy_check` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` |
| `ivyc` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
| `ivy_show` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` |
| `ivy_to_cpp` | `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` |
