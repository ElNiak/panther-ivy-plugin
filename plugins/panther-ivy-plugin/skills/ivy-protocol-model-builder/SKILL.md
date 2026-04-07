---
name: ivy-protocol-model-builder
description: "This skill should be used when the user asks to 'create an Ivy model', 'build a formal spec for a protocol', 'add a new protocol to panther_ivy', 'write Ivy tests for [protocol]', 'formalize [protocol] in Ivy', or wants to create a new protocol-testing directory with Ivy formal specifications. Guides classification, blueprint, and phased implementation with review checkpoints."
---

# Ivy Protocol Model Builder

> **Workspace**: Set active workspace with `/set-workspace <protocol>` before starting.

Interactive, phased workflow for creating a formal Ivy specification of any network protocol within panther_ivy. Covers protocol classification through test scenario creation. Assumes no Ivy experience — teaches constructs in context.

**Related skills**: `ivy-writing-guide` (Ivy syntax reference), `specification-patterns` (monitor patterns), `nct-methodology` (NCT/NACT/NSCT theory), `incremental-spec-dev` (incremental verification).

## Prerequisites

- panther_ivy submodule initialized
- Docker environment available for `ivyc target=test`
- The QUIC reference model at `protocol-testing/quic/` (200+ files)
- For Phases 5-6: at least one real protocol implementation to test against

## Phase Map

Six phases with mandatory checkpoints. Load the phase reference file at the start of each phase. Complete one phase before starting the next.

### Phase 1: Protocol Classification
**Load**: `references/phase-1-classification.md`

Ask 7 classification questions one at a time. Produce a protocol profile document. The profile resolves all architectural decisions for subsequent phases.

**STOP after Phase 1.** Present the protocol profile and pattern selection to the user. Do NOT proceed until the user confirms the classification is correct.

### Phase 2: Blueprint Generation
**Load**: `references/phase-2-blueprint.md`

Generate directory tree, module dependency graph, and RFC-to-Ivy type mapping table adapted to the protocol profile.

**STOP after Phase 2.** Present the file tree, dependency graph, and type mapping. Do NOT write any `.ivy` files until the user approves the architecture.

### Phase 3: Core Types and Stack
**Load**: `references/phase-3-core-types.md`

Write types, message structs, state tracking, and aggregator files. Verify with `ivy_verify` MCP tool (or `ivy_check` CLI). Consult `ivy-writing-guide` skill for syntax reference.

**STOP after Phase 3.** Run verification on the aggregator file. Present results and files to user. Do NOT proceed until user confirms type mappings match the RFC.

### Phase 4: Entity Model
**Load**: `references/phase-4-entity-model.md`

Create endpoint modules, entity files, base shim, role-specific shims, and serialization stubs. Verify with `ivy_compile` MCP tool (or `ivyc target=test` CLI).

**STOP after Phase 4.** Compile a minimal test file. Present the compilation result. Do NOT proceed until user reviews entity architecture.

### Phase 5: Behavioral Specs
**Load**: `references/phase-5-behavioral-specs.md`

Extract RFC requirements, write `around`/`before` advice with `require` statements and `_generating` guards. Write role-specific behavioral files. Consult `specification-patterns` skill for monitor patterns.

**STOP after Phase 5.** Run compiled test against a real implementation. Present pass/fail results. Do NOT proceed until user confirms the requirement-to-`require` mapping.

### Phase 6: Test Scenarios
**Load**: `references/phase-6-test-scenarios.md`

Create conformance tests, feature-specific tests, error handling tests, and (conditionally) attack tests. Consult `nct-methodology` or `nact-methodology` skill for test design patterns.

**STOP after Phase 6.** Run the full test suite. Present results. User reviews pass/fail and confirms model is complete.

## MCP Tool Integration

Use panther-ivy-plugin MCP tools throughout:

| Phase | MCP Tool | Purpose |
|-------|----------|---------|
| 3 | `ivy_verify` | Validate types and state definitions |
| 3-4 | `ivy_diagnostics(mode="structural")` | Fast structural checks after each file |
| 4 | `ivy_compile(target="test")` | Compile to test binary |
| 5 | `ivy_coverage(mode="gaps")` | Find uncovered RFC requirements |
| 5-6 | `ivy_coverage(mode="matrix")` | Requirement-to-assertion mapping |
| 6 | `ivy_patterns(mode="check")` | Layer/pattern completeness |

## Reference Files

For detailed phase instructions and Ivy tutorials:
- **`references/phase-1-classification.md`** — Protocol profiling questions, pattern selection
- **`references/phase-2-blueprint.md`** — File tree templates, module DAG, type mapping
- **`references/phase-3-core-types.md`** — Ivy type system tutorial, build order, checkpoints
- **`references/phase-4-entity-model.md`** — Endpoint/shim/serialization/behavior patterns
- **`references/phase-5-behavioral-specs.md`** — around/require/_generating, RFC extraction, debugging
- **`references/phase-6-test-scenarios.md`** — Test taxonomy, export/weight/finalize, attack models
- **`references/ivy-quick-reference.md`** — Language construct table (28 entries)
- **`references/panther-ivy-infrastructure.md`** — Built-in modules, compilation pipeline

## Worked Example

**`examples/dns_types.ivy`** — Minimal DNS-over-UDP types file demonstrating Phase 3 output.
