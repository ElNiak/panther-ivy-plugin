# Post-dispatch sample-verify gate

After a workflow specialist (verifier/builder/reviewer/triage/meta) returns a digest with assertable claims, the orchestrator MUST sample-verify the highest-leverage claims before integrating findings into memory or moving to the next phase. The gate exists because critic dispatches see only the digest, not the specialist's tool-call history — silent claim drift survives even a 3-of-3 SOUND vote unless the orchestrator independently confirms ground truth. Schema and naming intentionally mirror the critic `CITATION_*` mandate so the two layers compose into uniform claim-verification at both ends of every dispatch.

## When the gate fires

Per workflow tag (Option 2.2-ii from the design plan):

| Workflow | Gate fires? | Rationale |
|---|---|---|
| review (`ivy-reviewer-agent`) | yes | digests carry coverage tables, file:line citations, RFC quotes — assertion-dense |
| refine (`ivy-refiner-agent`) | yes | digests carry verification verdicts and counterexample interpretations |
| experiment (`ivy-experimenter-agent`) | yes | digests carry trace-analysis classifications and pcap-cross-validated wire claims |
| scaffold (`ivy-builder-agent`) | yes | digests carry layer-completeness claims, scaffold paths |
| triage (`ivy-triage-agent`) | skipped at orchestrator | G7 (post-diagnose) + G8 (post-fix) inline gates inside `triage-ops` already cover triage claims; orchestrator gate would double-check |
| meta (`ivy-meta-agent`) | skipped | editorial output (implementer + 2 reviewers), not assertion-dense |

## What counts as an assertable claim

Anything reality-based that can be re-read cheaply: file:line citations, RFC text quotes, integer counts (coverage %, file counts, manifest entries), specific commit hashes, on-disk file existence claims.

NOT an assertable claim: narration of process ("I dispatched ivy-coverage; output is below"), opinions, recommendations, prose summaries that don't reference a file or count.

## Sampling rule

Pick `N = min(3, ceil(claim_count / 5))` highest-leverage claims. The "highest-leverage" criterion is: claims whose falsity would change the orchestrator's next action. Skip trivially-derivable claims (process narration). For each sampled claim, run a cheap verification matched to the claim type:

| Claim type | Verification |
|---|---|
| file:line citation | `Read(file, offset=line)` and confirm content matches |
| RFC quote | `ivy_rfc(mode="section")` or grep against the cached RFC text |
| count (coverage %, file count) | re-run the producing tool (`ivy_coverage(mode="stats")`, `ls \| wc -l`) |
| file existence | `ls` or `Read` (Read errors confirm absence) |

## Verdict schema

Mirrors the critic `CITATION_*` contract for symmetry:

- `SAMPLE_PASS(<claim>, <evidence>)` — claim verified; cite the tool result that confirmed it
- `SAMPLE_FAIL(<claim>, <expected>, <observed>)` — claim contradicted by ground truth
- `SAMPLE_ABSTAIN(<claim>, <reason>)` — could not access target

## Integration rule

| Verdict distribution | Orchestrator action |
|---|---|
| All `SAMPLE_PASS` | Integrate findings into memory as-is |
| Any `SAMPLE_FAIL` | Reject the claim. Re-dispatch the specialist once with the falsifying evidence in `prior_findings`. Do NOT integrate yet. |
| All `SAMPLE_ABSTAIN`, or `SAMPLE_PASS` + `SAMPLE_ABSTAIN` (no FAIL) | Integrate with explicit caveat in the memory entry's frontmatter `description:` field naming the unverifiable claim |

## Anti-pattern guard

Do not sample-verify trivially-derivable claims:

- "I ran ivy_coverage and the output is below" → skip; the output is the evidence.
- "I see 44 .ivy files in scope" when the workspace context already reported 44 → skip; the count is dependent.
- "The file foo.ivy exists" when the previous Edit just touched it → skip; existence is implicit.

Sampling effort goes to claims that *could* be wrong, not claims that are definitionally true.

## Failure recovery

Bounded retry: a `SAMPLE_FAIL` triggers one re-dispatch of the specialist with the falsifying evidence in `prior_findings`. If the second specialist run produces the same claim, escalate to the user via `AskUserQuestion` (accept-with-caveat / re-dispatch-with-broader-context / abandon). No automated appeal path: the orchestrator's reading is authoritative; if the orchestrator's verification was wrong (stale tree, etc.) the user is the only override.

This bounded-retry policy is shared with the triage G7/G8 gates per the cross-phase design.

## Journal protocol

Each gate firing emits journal entries via `ivy_workflow_state(action="append_journal", ...)`:

- Before sampling: `progress{kind: "sample_verify_start", workflow: "<name>", claim_count: <int>, sampled: <N>}`
- Per-claim verdict: `progress{kind: "sample_verdict", verdict: "PASS"|"FAIL"|"ABSTAIN", claim_summary: "<short>"}`
- On reject + re-dispatch: `decision{summary: "Re-dispatch <agent> after SAMPLE_FAIL", context: "<falsifying evidence>"}`

These reuse the cluster-7 structured `progress` payload schema so `/nct-observability` surfaces them natively.

## Relationship to other rules

- `completion-gate.md` (5-step IDENTIFY → RUN → READ → VERIFY → THEN-claim): a `SAMPLE_FAIL` triggers a fresh IDENTIFY on the orchestrator side ("claim X did not pass sample-verify; re-state the work needed").
- `parallel-dispatch.md` (2-of-3 vote): orthogonal — sample-verify is run by the orchestrator alone, not by parallel agents. The critic CITATION_* mandate inside each parallel critic and SAMPLE_* in the orchestrator together bracket every dispatch.
- `agent-dispatch.md` (failure-recovery contract): SAMPLE_FAIL re-dispatch reuses the canonical retry pattern (auto-retry once for transient failures, AskUserQuestion thereafter).
- `mcp-tool-reliability.md` (cluster 12): if the verification tool itself fails (`InputValidationError`), follow the `ToolSearch select` recovery before treating the claim as `SAMPLE_ABSTAIN`.
