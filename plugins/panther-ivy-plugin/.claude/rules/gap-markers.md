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
- **`.yaml` files** (e.g., `scaffold-state.yaml`) — embed ONLY as a YAML comment using `# [GAP: …]` at end of a key line. Never insert a bare `[GAP: …]` token into a YAML document — bracket syntax is a flow sequence in YAML and corrupts parsing. Multi-line GAP rationale on YAML belongs in a leading `# [GAP: …]` comment block above the key.
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

Each `gate_verdict` event with `verdict: UNSOUND` records the number of `[GAP:]` markers written. The `render/summary/main.py` Stop hook can aggregate these counts across a session so the final summary reports: "N GAPs across M files, L of which were resolved this session".

## Interaction with the trigger-eval

GAP markers should never appear in a trigger-eval dispatch test (`evals/g*_trigger_eval.json`). An eval prompt that triggers a gate must either confirm `SOUND` on known-clean fixtures or confirm `UNSOUND` on known-dirty fixtures; the presence of `[GAP:]` in a fixture file's code region biases dispatch. Keep fixtures pristine; let the eval probe verify that the gate fires and writes the expected marker.

## Anti-patterns

- **Remove a `[GAP:]` marker only after committing the fix and re-running the gate to confirm SOUND.** Removing the marker without addressing the underlying issue trips `#403 error whitelisted via comment-out` on the next G4 run.
- **Return a verdict record `UNSOUND(#NN, reason, file:line)` from the critic; the orchestrator writes `[GAP:]` markers via Edit.** Critics return verdict records; only the orchestrator writes to the file.
- **Use `[GAP:]` exclusively for adversarial-gate unsound-specification markers. Use `// TODO` or GitHub issues for design intent.** Those belong in `// TODO` or in an issue tracker. `[GAP:]` is reserved for adversarial-gate output.
- **Do not stack multiple `[GAP:]` markers on the same line.** If a single line triggers multiple patterns, use one marker per pattern on consecutive lines above the code, or merge the reasons into one marker that cites the lowest-numbered pattern and mentions the others in the reason text.
