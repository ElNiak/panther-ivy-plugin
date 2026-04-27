---
paths: ["**/*.ivy"]
---

# GAP markers

An adversarial quality gate (G1 exploration, G2 per-layer modeling, G3 test-spec, G4 verification, G5 IUT trace analysis) emits a `[GAP: #NN <reason>]` marker inline in the affected artifact whenever it returns `VERDICT_UNSOUND`. A GAP marker is a contract: the next revise cycle MUST address it before the gate can pass.

## Syntax

```
[GAP: #NN <short reason>]
```

- `#NN` references an entry in the `ivy-error-patterns` skill's numbered catalog (`verifier_patterns.md`). Every GAP marker cites exactly one pattern ID.
- `<short reason>` is a single-line explanation in plain English (no line breaks).
- A marker is placed at the file:line location the critic identified, appended to the existing line or on a dedicated line above it.

## Per-format placement rules

The marker MUST be embedded in a way the host file's parser ignores. The orchestrator selects placement based on file extension:

- **`.ivy` files** — append after the relevant line as a `# [GAP: …]` comment (Ivy uses `#` as line comments). Or place a comment line above the cited construct. Inline trailing form is preferred when the line is short.
- **`.yaml` files** (e.g., `build-state.yaml`) — embed ONLY as a YAML comment using `# [GAP: …]` at end of a key line. Never insert a bare `[GAP: …]` token into a YAML document — bracket syntax is a flow sequence in YAML and corrupts parsing. Multi-line GAP rationale on YAML belongs in a leading `# [GAP: …]` comment block above the key.
- **`.md` / scope notes** — embed as `<!-- [GAP: …] -->` HTML comment OR as a normal `> [GAP: …]` blockquote line (clearly authored, not consumed by markdown formatters).
- **`.json` files** — JSON has no comment syntax. Do NOT write GAP markers into JSON. Surface the finding in the verdict block and journal entry only.

The orchestrator must enforce these rules before calling `Edit`. A critic that proposes a GAP location in a JSON file must be re-routed to verdict-only output.

Example (Ivy, after fix proposal):

```ivy
action handle_open(msg : open_msg) = {
    local_state := msg.payload  # [GAP: #250 missing re-entry guard — action is exported and state is mutated before any require]
    ...
}
```

Example (YAML, after fix proposal):

```yaml
layers:
  bgp_open:
    file: bgp_stack/bgp_open.ivy
    status: pending  # [GAP: #101 RFC 4271 §6.3 OPEN-message MUST clauses unmapped]
```

## Who writes GAP markers

Only the **orchestrator** (the workflow phase code that fans out critics and aggregates verdicts) writes GAP markers to a file. A critic returns a verdict record `UNSOUND(#NN, "<reason>", "<file:line>")` but does not perform `Edit` operations itself. This keeps the write surface small and auditable, and it ensures every GAP is traceable to a specific gate invocation via the journal.

## Relationship to claim-discussion prefixes

The `claim-discussion` skill already defines a set of inline resolution prefixes. A GAP marker is a **new** state that precedes them; it is not a replacement. Lifecycle:

| Marker | Meaning | Written by | Removed when |
|---|---|---|---|
| `[GAP: #NN <reason>]` | Adversarial gate found an unsound spot; not yet resolved | Orchestrator | The next `Edit` at that location fixes the issue and the gate re-runs returning `SOUND` (orchestrator removes the marker) |
| `// RESOLVED YYYY-MM-DD: …` | A claim discussion concluded the spec is correct as-is | Author | Permanent unless the code it annotates changes |
| `// IUT_FINDING YYYY-MM-DD: …` | Verification failure was an IUT bug, not a model bug | Author | Permanent; tracked separately |
| `// DEFERRED YYYY-MM-DD: …` | Known gap, deliberately deferred with rationale | Author (user decision) | Permanent until author removes it |
| `// GUARD_ADDED YYYY-MM-DD: …` | A `require` was added to address a gap | Author | Permanent |
| `// KNOWN_DEVIATION YYYY-MM-DD: …` | Spec deliberately diverges from RFC; rationale recorded | Author | Permanent |
| `// N/A YYYY-MM-DD: …` | Discussion does not apply | Author | Permanent |

## Promotion rules

A `[GAP:]` marker may be promoted to a `claim-discussion` prefix by a deliberate author action:

- **To `// DEFERRED YYYY-MM-DD:`** — author accepts the gap and records why a fix is deferred. Remove the `[GAP:]` token, add a `// DEFERRED` line with rationale, commit. The orchestrator will not re-raise the same pattern at this location.
- **To `// RESOLVED YYYY-MM-DD:`** — the code has been fixed. Re-run the gate; on `VERDICT_SOUND` the orchestrator removes the `[GAP:]` automatically. If the author adds an explanatory `// RESOLVED` comment describing the fix, that is preserved.
- **To `// IUT_FINDING YYYY-MM-DD:`** — trace analysis concluded the issue is an IUT bug, not a spec bug. Author writes the `// IUT_FINDING` comment citing the pattern ID and removes the `[GAP:]`. The IUT finding is tracked in the run's `analysis_results.json` but the spec is considered correct at that location.

**Promotion is always a user action.** Gates never promote markers automatically. A `[GAP:]` that has been sitting on a line for multiple cycles is information — the orchestrator reports it but does not decide its fate.

## Listing GAP markers

Greppable across a workspace:

```bash
grep -rn "\[GAP:" panther/plugins/services/testers/panther_ivy/protocol-testing/
```

Per-protocol:

```bash
grep -rn "\[GAP:" protocol-testing/bgp/
```

## GAP count in workflow-journal

Each `gate_verdict` event with `verdict: UNSOUND` records the number of `[GAP:]` markers written. The `render-summary.py` Stop hook can aggregate these counts across a session so the final summary reports: "N GAPs across M files, L of which were resolved this session".

## Interaction with the trigger-eval

GAP markers should never appear in a trigger-eval dispatch test (`evals/g*_trigger_eval.json`). An eval prompt that triggers a gate must either confirm `SOUND` on known-clean fixtures or confirm `UNSOUND` on known-dirty fixtures; the presence of `[GAP:]` in a fixture file's code region biases dispatch. Keep fixtures pristine; let the eval probe verify that the gate fires and writes the expected marker.

## Anti-patterns

- **Remove a `[GAP:]` marker only after committing the fix and re-running the gate to confirm SOUND.** Removing the marker without addressing the underlying issue trips `#403 error whitelisted via comment-out` on the next G4 run.
- **Return a verdict record `UNSOUND(#NN, reason, file:line)` from the critic; the orchestrator writes `[GAP:]` markers via Edit.** Critics return verdict records; only the orchestrator writes to the file.
- **Use `[GAP:]` exclusively for adversarial-gate unsound-specification markers. Use `// TODO` or GitHub issues for design intent.** Those belong in `// TODO` or in an issue tracker. `[GAP:]` is reserved for adversarial-gate output.
- **Do not stack multiple `[GAP:]` markers on the same line.** If a single line triggers multiple patterns, use one marker per pattern on consecutive lines above the code, or merge the reasons into one marker that cites the lowest-numbered pattern and mentions the others in the reason text.
