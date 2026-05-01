---
description: Experiment workflow anti-patterns (Red Flags). Auto-loads on experiment-ops skill entry. Each row pairs a tempting thought with the calibrated correct behavior. Skill body is leaner because this content lives here, not duplicated in SKILL.md.
paths: ["**/skills/experiment-ops/SKILL.md"]
---

<purpose>
Experiment-workflow anti-patterns covering IUT execution and 9-step trace
analysis (NCT phase 10). Promoted to an auto-loaded rule so the skill body
stays focused on phase mechanics; the anti-pattern catalog auto-loads on
every experiment-ops skill entry.
</purpose>

## Red Flags — Experiment

| Thought | Reality |
|---|---|
| "The IUT trace matches the Ivy log, skip pcap" | Ivy log events do not guarantee wire transmission. Always cross-validate via pcap (G5 catalog `#501`). |
| "This counterexample is a model bug, not the IUT" | Distinguish IUT bug vs. model bug via the G5 trace gate (`#505`). Do not classify without the gate. |
| "G5 will fire from the post-tool hook, I'll skip the inline dispatch" | The experimenter dispatches G5 inline on every IUT-test outcome. The `assess-trace.py` hook is a backstop only; inline dispatch is what the workflow consumes for its verdict. |
| "I'll just run ivyc directly to compile the test" | Per `feedback_never_run_ivyc_directly`: always use `ivy_compile` MCP (or `panther run` for full experiments). The CLI lacks staging and include setup. |
| "I'll execute the Ivy binary directly" | Per `feedback_use_panther_run`: never execute Ivy binaries directly. Use `panther run` (preferred for long-form) or `ivy_iut_test` (MCP shortcut). |
| "panther run is taking a while, let me kill it and retry" | Per `feedback_monitor_background_panther`: spawn a Monitor or background subagent on any panther run that may exceed 60 seconds. Do not kill mid-run; outputs are partial and the failure may be intermittent. |
| "Tester passed, that's all the analysis I need" | Per `feedback_always_analyze_iut_logs`: run the 9-step analysis (assertions, stderr, IUT logs, pcap) after every panther run, even on PASS. The verdict by itself is not sufficient. |
| "I'll classify TESTER_CRASH as IUT_CRASH since the symptom looks similar" | Catalog `#505`: misattributing tester crashes to IUT bugs corrupts the bug-finder reputation. Cite the G5 verdict before classifying. |
| "STALENESS_RULE doesn't apply to IUT runs" | If the spec or IUT was rebuilt since the last run, the result is stale. Re-run before reporting a verdict. |
