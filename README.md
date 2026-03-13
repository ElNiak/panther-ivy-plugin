# panther-ivy-plugin

NCT/NACT/NSCT methodology guidance for Ivy protocol testing via native Ivy LSP and ivy-tools MCP server. Provides agents, skills, and commands for formal protocol specification, attack modeling, and simulation-based testing using the 14-layer template architecture.

**Version:** 0.1.0 | **License:** MIT | **Author:** [ElNiak](https://github.com/ElNiak)

## Overview

This is a **Claude Code plugin** for the PANTHER-Ivy tester. It provides methodology guidance, domain knowledge, and interactive tooling for formal protocol testing using Microsoft's IVy language.

**What it does:**
- Guides users through three testing methodologies (NCT, NACT, NSCT) with interactive agents
- Provides domain knowledge via skills (Ivy language, 14-layer template, RFC mapping, tool catalogs)
- Offers slash commands for common operations (verify, compile, scaffold, inspect)
- Enforces MCP tool usage over direct CLI invocations via a PreToolUse hook

**What it does NOT do:**
- Install Ivy, Z3, or the Ivy toolchain (these live in Docker containers managed by PANTHER)
- Build Docker images or run experiments (use the PANTHER CLI for that)
- Replace the Ivy compiler or verifier (it wraps them via MCP)

### Three Methodologies

| Methodology | Full Name | Purpose |
|-------------|-----------|---------|
| **NCT** | Network-Centric Compositional Testing | Formal spec plays one protocol role against an Implementation Under Test (IUT) to verify RFC compliance |
| **NACT** | Network-Attack Compositional Testing | Extends NCT with the APT 6-stage lifecycle to model and test protocols from an attacker's perspective |
| **NSCT** | Network-Simulator Centric Compositional Testing | Runs the same Ivy specs inside Shadow Network Simulator for deterministic, large-scale, topology-controlled testing |

## Prerequisites

- **PANTHER framework** with the Ivy tester plugin installed (`panther/plugins/services/testers/panther_ivy/`)
- **Ivy toolchain** available (either locally or via Docker-based execution through PANTHER)
- **Native Ivy LSP** (configured automatically via `.lsp.json`) -- diagnostics, go-to-definition, find-references, hover for `.ivy` files
- **ivy-tools MCP server** (configured automatically via `.mcp.json`):
  - [ivy-tools](https://github.com/ElNiak/ivy-lsp) -- Ivy verification, compilation, analysis, linting, and traceability tools

## Installation

Claude Code auto-discovers plugins via the `.claude-plugin/` directory. No `pip install` is needed for the plugin itself.

1. Ensure the panther-ivy-plugin is present as a submodule (or cloned) at `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`
2. The `.mcp.json` file configures the `ivy-tools` MCP server and the `.lsp.json` file configures the native Ivy LSP
3. Claude Code will automatically load the plugin's agents, skills, commands, and hooks

## Components

| Component | Count | Description | Details |
|-----------|-------|-------------|---------|
| Agents | 9 | Methodology guides, utility agents, and quality evaluation | [agents/](agents/) |
| Commands | 6 | Slash commands for verification, compilation, and scaffolding | [commands/](commands/) |
| Skills | 12 | Domain knowledge for Ivy language, methodologies, and tooling | [skills/](skills/) |
| Hooks | 3 | PreToolUse (block CLI), PostToolUse (lint .ivy), SubagentStop (quality gates) | -- |

## Tooling Architecture

The plugin relies on one MCP server plus native LSP support:

| Component | Role | Capabilities | Source |
|-----------|------|--------------|--------|
| **Native Ivy LSP** | Language intelligence for `.ivy` files | Diagnostics, go-to-definition, find-references, hover | [ivy-lsp](https://github.com/ElNiak/ivy-lsp) (configured via `.lsp.json`) |
| **ivy-tools MCP** | Verification, analysis, and visualization | `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_lint`, `ivy_traceability_matrix`, `ivy_requirement_coverage`, `ivy_impact_analysis` | [ivy-lsp](https://github.com/ElNiak/ivy-lsp) (configured via `.mcp.json`) |
| **Claude's native tools** | Code navigation and editing | `Read`, `Edit`, `Write`, `Grep`, `Glob`, `Bash` | Built into Claude Code |

A **PreToolUse hook** (`hooks/scripts/block-direct-ivy.sh`) intercepts Bash tool calls and blocks direct invocations of `ivy_check`, `ivyc`, `ivy_show`, and `ivy_to_cpp`, redirecting to the corresponding MCP tool. This ensures all Ivy operations go through the MCP server for consistent behavior and structured output.

A **PostToolUse hook** (`hooks/scripts/post-write-ivy-lint.sh`) runs fast structural checks on `.ivy` files after Write/Edit operations, providing immediate feedback on missing `#lang` headers or unbalanced braces.

**SubagentStop hooks** automatically evaluate agent outputs when they finish: write agents (nct-guide, nact-guide, nsct-guide, requirement-extractor) are evaluated for structural quality, traceability, and manifest correctness via an agent hook; read agents (spec-explorer, ivy-model-reviewer, traceability-reviewer, spec-verifier) are evaluated for factual accuracy and completeness via a prompt hook. Failed evaluations trigger one self-repair retry before escalating to the user.

## Quick Start

**Explore an existing model:**
```
/nct-model-info file=protocol-testing/quic/quic_stack/quic_connection.ivy
```

**Verify a specification file:**
```
/nct-check file=protocol-testing/quic/quic_stack/quic_packet.ivy
```

**Scaffold a new protocol:**
```
/nct-new-protocol name=coap
```

For interactive guidance, ask Claude directly -- the agents activate automatically:
- "Walk me through the QUIC protocol specification structure" (triggers `spec-explorer`)
- "I need to write an Ivy specification for the CoAP protocol" (triggers `nct-guide`)
- "Which MUST requirements from RFC 9000 are we missing?" (triggers `traceability-reviewer`)

## Methodology Overview

| | NCT | NACT | NSCT |
|---|-----|------|------|
| **Description** | Formal spec plays one role against an IUT to verify RFC compliance | Extends NCT with APT lifecycle to model attacks | Runs specs in Shadow NS for deterministic, large-scale testing |
| **Guide Agent** | `nct-guide` | `nact-guide` | `nsct-guide` |
| **Methodology Skill** | `nct-methodology` | `nact-methodology` | `nsct-methodology` |
| **Key Concepts** | Role inversion, before/after monitors, `_finalize`, Z3/SMT | APT 6-stage lifecycle, attack entities, protocol bindings | Shadow NS, topology control, deterministic replay, scale testing |
| **Typical Workflow** | 10-step: RFC analysis to compiled test binary | 9-step: threat model to attack test binary | NCT specs + Shadow NS config for simulated execution |

## Related Projects

| Project | Description | Relationship |
|---------|-------------|--------------|
| [ivy-lsp](https://github.com/ElNiak/ivy-lsp) | Ivy Language Server Protocol implementation and MCP tool server | Provides both the native Ivy LSP (`.lsp.json`) and the `ivy-tools` MCP server (`.mcp.json`) used by this plugin |
| [PANTHER](https://github.com/ElNiak/PANTHER) | Protocol Analysis and Testing Harness for Extensible Research | Parent framework; the Ivy tester plugin is a PANTHER service |
| PANTHER-Ivy | Ivy tester plugin for PANTHER (`panther_ms_ivy`) | The Docker-based tester that this Claude Code plugin provides guidance for |

## Directory Structure

```
panther-ivy-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest (name, version, description)
├── .lsp.json                # Native Ivy LSP configuration
├── .mcp.json                # ivy-tools MCP server configuration
├── agents/                  # 9 agent definitions
│   ├── README.md            # Agent catalog and selection guide
│   ├── spec-explorer.md     # Navigate and explain Ivy specifications
│   ├── nct-guide.md         # NCT methodology workflow guide
│   ├── nact-guide.md        # NACT methodology workflow guide
│   ├── nsct-guide.md        # NSCT methodology workflow guide
│   ├── spec-verifier.md     # Verification and diagnosis specialist
│   ├── ivy-model-reviewer.md # Model quality reviewer
│   ├── requirement-extractor.md # RFC requirement extraction
│   ├── traceability-reviewer.md # RFC coverage audit
│   └── quality-gate.md      # Quality evaluation agent
├── commands/                # 6 slash commands
│   ├── README.md            # Command reference and workflows
│   ├── nct-check.md         # /nct-check -- formal verification
│   ├── nct-compile.md       # /nct-compile -- compile to test binary
│   ├── nct-model-info.md    # /nct-model-info -- model structure
│   ├── nct-new-test.md      # /nct-new-test -- scaffold test spec
│   └── nct-new-protocol.md  # /nct-new-protocol -- scaffold protocol
├── hooks/
│   ├── hooks.json           # Hook definitions (PreToolUse, PostToolUse, SubagentStop)
│   └── scripts/
│       ├── block-direct-ivy.sh      # Blocks direct Ivy CLI, redirects to MCP
│       └── post-write-ivy-lint.sh   # Fast structural lint after .ivy writes
├── skills/                  # 12 skill directories
│   ├── README.md            # Skill catalog and learning paths
│   ├── 14-layer-template/   # Protocol decomposition template
│   ├── annotated-spec-writing/ # RFC bracket-tag annotations
│   ├── ivy-model-editing/   # Ivy language reference
│   ├── ivy-tools-reference/ # ivy-tools MCP tool catalog
│   ├── ivy-verification/    # Verification workflow guide
│   ├── nact-methodology/    # NACT methodology
│   ├── nct-methodology/     # NCT methodology
│   ├── nsct-methodology/    # NSCT methodology
│   ├── ivy-tooling-guide/    # Ivy tooling architecture and tool mapping
│   ├── rfc-to-ivy-mapping/  # RFC to Ivy translation patterns
│   ├── quality-gate-reference/ # Quality evaluation pipeline reference
│   └── writing-test-specs/  # Test specification guide
└── README.md                # This file
```

## License

MIT
