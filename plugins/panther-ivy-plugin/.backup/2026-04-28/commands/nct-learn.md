---
name: nct-learn
description: "Manually trigger knowledge capture to extract and persist session learnings to plugin rules"
arguments: []
---

<purpose>
Manual trigger for the knowledge-capture skill. Use this when you want
to capture learnings outside of the automatic knowledge gates embedded
in workflow skills.
</purpose>

<metadata mode="FAST" orchestrator="false" workspace-aware="false"/>

<instructions>
  <step n="1">Dispatch the knowledge-capture skill with no args:</step>
</instructions>

<dispatch target="knowledge-capture" via="skill"
          reason="manual knowledge capture trigger (/nct-learn)"/>

```
Skill(skill="panther-ivy-plugin:cross-cutting-knowledge-capture")
```

The skill runs the full 5-step knowledge capture flow: scan existing rules, reflect on the current session, classify learnings, spawn the classification reviewer agent, and present candidates for user confirmation.
