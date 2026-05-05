# panther-ivy-plugin

NCT/NACT/NSCT methodology guidance for Ivy protocol testing via native Ivy LSP and ivy-tools MCP server. Provides agents, skills, and commands for formal protocol specification, attack modeling, and simulation-based testing using the 14-layer template architecture.

**Version:** 0.10.0 | **License:** MIT | **Author:** [ElNiak](https://github.com/ElNiak)

## Overview

This is a **Claude Code plugin** for the PANTHER-Ivy tester. It provides methodology guidance, domain knowledge, and interactive tooling for formal protocol testing using Microsoft's IVy language.

**What it does:**
- Guides users through three testing methodologies (NCT, NACT, NSCT) with interactive agents
- Provides domain knowledge via skills (Ivy language, 14-layer template, RFC mapping, tool catalogs)
- Offers slash commands for common operations (verify, compile, inspect, health, observability)
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
- **Native Ivy LSP** (configured automatically via `.lsp.json`) -- go-to-definition, find-references, hover, document symbols for `.ivy` files (diagnostics via MCP `ivy_diagnostics`)
- **ivy-tools MCP server** (configured automatically via `.mcp.json`):
  - [ivy-tools](https://github.com/ElNiak/ivy-lsp) -- Ivy verification, compilation, analysis, linting, and traceability tools

## Installation

Claude Code auto-discovers plugins via the `.claude-plugin/` directory. No `pip install` is needed for the plugin itself.

1. Ensure the panther-ivy-plugin is present as a submodule (or cloned) at `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`
2. The `.mcp.json` file configures the `ivy-tools` MCP server and the `.lsp.json` file configures the native Ivy LSP
3. Claude Code will automatically load the plugin's agents, skills, commands, and hooks

## Components

Counts below are computed by `plugins/panther-ivy-plugin/scripts/inventory_counts.py` and verified by `tests/test_readme_counts.py`. Update both the script's output and this table together when components change.

| Component | Count | Description | Details |
|-----------|-------|-------------|---------|
| Agents | 9 (6 specialist + 3 critic) | Specialists (`ivy-builder`, `ivy-experimenter`, `ivy-meta`, `ivy-refiner`, `ivy-reviewer`, `ivy-triage`) handle workflow execution; critics (`g-plan`, `g-fidelity`, `g-knowledge`) run adversarial-vote gates | [agents/](plugins/panther-ivy-plugin/agents/) |
| Commands | 2 (shortcuts) | `/nct-health` (9-step diagnostic runbook), `/nct-iut-test` (IUT experiment via PANTHER) | [commands/](plugins/panther-ivy-plugin/commands/) |
| Skills | 15 (1 orchestrator + 6 ops + 8 knowledge) | Orchestrator (`ivy`) routes intent; ops skills (`scaffold-ops`, `refine-ops`, `experiment-ops`, `review-ops`, `triage-ops`, `meta-self-mod-ops`) own workflow procedures; knowledge skills (`methodology`, `specification-patterns`, `propagation-patterns`, `ivy-syntax`, `ivy-toolkit`, `verification-failures`, `apt-attack-patterns`, `reference-drift`) provide domain references | [skills/](plugins/panther-ivy-plugin/skills/) |
| Hooks | 46 commands / 38 matchers across 12 events | PreToolUse, PostToolUse, PostToolUseFailure, SessionStart/End, Stop, SubagentStart/Stop, PreCompact, UserPromptSubmit, Notification, PermissionRequest | [hooks/](plugins/panther-ivy-plugin/hooks/) |
| Rules | 15 | Auto-loaded `.claude/rules/` files (iron-laws, agent-dispatch, journaling-contract, gate-verdicts, ivy-formatting, plan-mode, output-style, mcp-tool-reliability, postuse-hook-ordering, propagation-authority, gap-markers, skill-conventions, scaffold-anti-patterns, refine-anti-patterns, experiment-anti-patterns) | [.claude/rules/](plugins/panther-ivy-plugin/.claude/rules/) |

## Tooling Architecture

The plugin relies on one MCP server plus native LSP support:

| Component | Role | Capabilities | Source |
|-----------|------|--------------|--------|
| **Native Ivy LSP** | Language intelligence for `.ivy` files | Diagnostics, go-to-definition, find-references, hover | [ivy-lsp](https://github.com/ElNiak/ivy-lsp) (configured via `.lsp.json`) |
| **ivy-tools MCP** | Verification, analysis, and visualization | `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_lint`, `ivy_coverage`, `ivy_query`, `ivy_visualize`, `ivy_quality`, `ivy_patterns` | [ivy-lsp](https://github.com/ElNiak/ivy-lsp) (configured via `.mcp.json`) |
| **Claude's native tools** | Code navigation and editing | `Read`, `Edit`, `Write`, `Grep`, `Glob`, `Bash` | Built into Claude Code |

A **PreToolUse hook** (`hooks/scripts/block-direct-ivy.sh`) intercepts Bash tool calls and warns about direct invocations of `ivy_check`, `ivyc`, `ivy_show`, and `ivy_to_cpp`, suggesting the corresponding MCP tool. This encourages all Ivy operations to go through the MCP server for consistent behavior and structured output.

A **PostToolUse hook** (`hooks/scripts/post-write-ivy-lint.sh`) runs fast structural checks on `.ivy` files after Write/Edit operations, providing immediate feedback on missing `#lang` headers or unbalanced braces.

A **SessionStart hook** (`hooks/scripts/detect-ivy-workspace.sh`) detects the Ivy workspace root and injects context for Claude, including the path to protocol models and MCP server scope.

## Quick Start

**Explore an existing model:**
```
/nct-model-info file=protocol-testing/quic/quic_stack/quic_connection.ivy
```

**Verify a specification file:**
```
/nct-check file=protocol-testing/quic/quic_stack/quic_packet.ivy
```

**Build a new protocol model:**
Ask Claude "I need to write an Ivy specification for the CoAP protocol" to activate the `build` workflow, which scaffolds layers, generates templates, and guides you through the 14-layer architecture.

For interactive guidance, ask Claude directly -- workflow routing activates automatically:
- "Walk me through the QUIC protocol specification structure" (activates `navigate` workflow)
- "I need to write an Ivy specification for the CoAP protocol" (activates `build` workflow)
- "Which MUST requirements from RFC 9000 are we missing?" (activates `review` workflow)

## Methodology Overview

| | NCT | NACT | NSCT |
|---|-----|------|------|
| **Description** | Formal spec plays one role against an IUT to verify RFC compliance | Extends NCT with APT lifecycle to model attacks | Runs specs in Shadow NS for deterministic, large-scale testing |
| **Entry Workflow** | `build` / `verify` | `build` / `verify` | `build` / `verify` |
| **Methodology Skill** | `methodology-reference` | `methodology-reference` | `methodology-reference` |
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
│   └── marketplace.json     # Marketplace metadata
├── plugins/
│   ├── ivy-lsp/
│   │   └── .lsp.json        # Native Ivy LSP configuration
│   └── panther-ivy-plugin/
│       ├── .claude-plugin/
│       │   └── plugin.json  # Plugin manifest (name, version, description)
│       ├── .mcp.json        # ivy-tools MCP server configuration
│       ├── .lsp.json        # LSP configuration (co-located)
│       ├── routing-rules.json # Smart routing rules for UserPromptSubmit hook
│       ├── settings.json    # Plugin settings
│       ├── agents/          # 9 agents: 6 specialist (ivy-*) + 3 critic (g-*)
│       │   ├── README.md
│       │   ├── ivy-builder-agent.md, ivy-experimenter-agent.md, ivy-meta-agent.md
│       │   ├── ivy-refiner-agent.md, ivy-reviewer-agent.md, ivy-triage-agent.md
│       │   └── g-plan-critic.md, g-fidelity-critic.md, g-knowledge-critic.md
│       ├── commands/        # 2 shortcut commands
│       │   ├── README.md
│       │   ├── nct-health.md        # /nct-health   -- 9-step diagnostic runbook
│       │   └── nct-iut-test.md      # /nct-iut-test -- IUT experiment via PANTHER
│       ├── hooks/
│       │   ├── hooks.json   # 46 commands / 38 matchers across 12 events
│       │   └── scripts/     # Hook implementations (Python; ~37 entry points + shared libs)
│       ├── skills/          # 15 skills: 1 orchestrator + 6 ops + 8 knowledge
│       │   ├── README.md
│       │   ├── ivy/                     # ORCHESTRATOR — session entry, warm resume, intent routing, gate-critic dispatch
│       │   ├── scaffold-ops/            # OPS — protocol model construction (NCT/NACT/NSCT scaffolding)
│       │   ├── refine-ops/              # OPS — Ivy spec verification (compile -> verify -> diagnose -> fix loop)
│       │   ├── experiment-ops/          # OPS — IUT execution + 9-step trace analysis
│       │   ├── review-ops/              # OPS — RFC coverage audit, quality scoring, traceability
│       │   ├── triage-ops/              # OPS — MCP/LSP/Serena health repair (9-step runbook)
│       │   ├── meta-self-mod-ops/       # OPS — plugin source modifications (skills, agents, hooks, rules)
│       │   ├── methodology/             # KNOWLEDGE — NCT / NACT / NSCT methodology reference
│       │   ├── specification-patterns/  # KNOWLEDGE — 14-layer template + scaffolding patterns
│       │   ├── propagation-patterns/    # KNOWLEDGE — type-change impact analysis + Ivy-to-C++ encoding
│       │   ├── ivy-syntax/              # KNOWLEDGE — Ivy 1.7 syntax + module system + RFC annotation
│       │   ├── ivy-toolkit/             # KNOWLEDGE — 18-tool MCP catalog + Serena semantic tools
│       │   ├── verification-failures/   # KNOWLEDGE — verifier-pattern catalog + counterexample interpretation
│       │   ├── apt-attack-patterns/     # KNOWLEDGE — NACT 6-stage attack lifecycle + around-block monitors
│       │   └── reference-drift/         # KNOWLEDGE — cross-reference audit (Skill/Agent calls, _KNOWN_* sets)
│       ├── scripts/         # Server startup + inventory + migration scripts
│       └── tests/           # Plugin test suite
└── README.md                # This file
```

## License

MIT
