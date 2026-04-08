# Skills

## Overview

Skills provide reference material and domain knowledge for Ivy protocol testing within the PANTHER framework. They are loaded by workflow skills and agents as needed -- not invoked directly by users.

## Workflow Skills (5)

User-facing entry points activated by the routing system or natural language.

| Skill | Purpose |
|-------|---------|
| [navigate](navigate/) | Session entry point -- detect intent, resume context, route to the right workflow |
| [verify](verify/) | Verify, compile, diagnose failures in Ivy specifications |
| [build](build/) | Create models, add layers, propagate type changes |
| [review](review/) | Audit quality, check RFC coverage, run multi-agent review |
| [triage](triage/) | Diagnose toolchain issues, health check LSP + MCP stack |

## Knowledge Skills (7)

Reference material loaded by workflows and agents on demand.

| Skill | Purpose |
|-------|---------|
| [counterexample-guide](counterexample-guide/) | Interpreting ivy_verify counterexample traces and identifying fixes |
| [specification-patterns](specification-patterns/) | 14-layer structural template and formal model pattern library |
| [propagation-patterns](propagation-patterns/) | Patterns for propagating type changes across ser/deser state machines |
| [ivy-writing-guide](ivy-writing-guide/) | Ivy language syntax, test spec patterns, RFC bracket-tag annotations |
| [ivy-toolkit](ivy-toolkit/) | Single source of truth for all MCP tool documentation and tool selection guidance |
| [claim-discussion](claim-discussion/) | Structured decision trees for verification claim resolution and coverage gap prioritization |
| [methodology-reference](methodology-reference/) | Comprehensive reference for NCT, NACT, NSCT methodologies |
