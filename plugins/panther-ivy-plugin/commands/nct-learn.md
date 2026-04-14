---
name: nct-learn
description: "Manually trigger knowledge capture to extract and persist session learnings to plugin rules"
arguments: []
---

> **Manual trigger** for the knowledge-capture skill. Use this when you want to capture learnings outside of the automatic knowledge gates embedded in workflow skills.

Invoke the `knowledge-capture` skill:

```
Skill(skill="panther-ivy-plugin:knowledge-capture")
```

This runs the full 5-step knowledge capture flow: scan existing rules, reflect on the current session, classify learnings, spawn the classification reviewer agent, and present candidates for user confirmation.
