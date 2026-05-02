# Experiment Session Summary

## Sections (in order)

### IUT Verdicts
- Per IUT run: IUT name, verdict (`NO_VIOLATION_FOUND` / `NON_COMPLIANT` / `TESTER_CRASH` / `IUT_CRASH`), duration
- Total runs: {run_count} | Violations: {non_compliant_count} | Crashes: {crash_count}

### Trace Findings
- Counts of NON_COMPLIANT per RFC section
- Counts of IUT_CRASH / TESTER_CRASH with triage hint
- Any pcap anomalies flagged during 9-step analysis

### Pending Refine
- Spec-bug discoveries (NON_COMPLIANT with RFC citation) to hand off to refine
- One line per finding: "{rfc_section}: {violation_summary}"

### Pending Review
- Coverage gaps surfaced during experiment analysis
- One line per gap: "{rfc_section}: not covered by any assertion"

### Session Metrics
- Total `panther run` invocations
- Session duration hint (from observability timestamps)
