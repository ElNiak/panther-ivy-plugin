---
name: nct-health
description: "Run the full 9-step Ivy LSP + MCP diagnostic runbook (content validation + phase reviews)"
arguments: []
---

Run the deep health-check runbook for the Ivy LSP + MCP integration stack by
dispatching the triage skill in its `full-health-check` mode. The runbook
lives at `skills/triage/references/full-health-check.md`; the skill body
branches on the argument. For quick preflight liveness checks use the plain
`/triage` workflow instead.

Skill(skill="panther-ivy-plugin:triage", args="full-health-check")
