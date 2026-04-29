---
name: nct-health
description: "Run the full 9-step Ivy LSP + MCP diagnostic runbook (content validation + phase reviews)"
arguments: []
---

<purpose>
Run the deep 9-step health-check runbook for the Ivy LSP + MCP
integration stack by dispatching the ivy-triage-agent for the full
9-step diagnostic. The runbook lives in the agent's preloaded
`triage-ops` operating procedure (`skills/triage-ops/references/`).
For quick preflight liveness checks, dispatch the agent with a
preflight intent instead.
</purpose>

<metadata mode="FAST" orchestrator="false" workspace-aware="false"/>

<dispatch target="ivy-triage-agent" via="agent" mode="full-health-check"
          reason="/nct-health — deep 9-step health-check runbook"/>

```
Agent(subagent_type="panther-ivy-plugin:ivy-triage-agent",
      description="Full 9-step Ivy LSP + MCP health check",
      prompt="Run the full 9-step Ivy LSP + MCP health-check runbook (full-health-check mode). Walk through every diagnostic step, report PASS/FAIL/WARN per step, and flag any repair actions that require user confirmation. Return under 800 words; JSON output per <output_schema>.")
```
