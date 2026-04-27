---
name: nct-health
description: "Run the full 9-step Ivy LSP + MCP diagnostic runbook (content validation + phase reviews)"
arguments: []
---

<purpose>
Run the deep 9-step health-check runbook for the Ivy LSP + MCP
integration stack by dispatching the triage skill in its
`full-health-check` mode. The runbook lives at
`skills/triage/references/full-health-check.md`; the skill body branches
on the argument. For quick preflight liveness checks, use the plain
`triage` workflow instead.
</purpose>

<metadata mode="FAST" orchestrator="false" workspace-aware="false"/>

<dispatch target="triage" via="skill" args="full-health-check"
          reason="/nct-health — deep 9-step health-check runbook"/>

```
Skill(skill="panther-ivy-plugin:workflow-triage", args="full-health-check")
```
