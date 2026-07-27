# Completion Gate (5-step IDENTIFY → RUN → READ → VERIFY → THEN-claim)

Use this gate before claiming any workflow completion ("verification passed", "build done", "review SOUND", "triage repaired"). Each step has a hard requirement; a missed step invalidates the claim.

## Step 1 — IDENTIFY

State the claim explicitly. One sentence. Examples:

- "Verification passed on protocol-testing/bgp/bgp_stack/bgp_connection.ivy."
- "Build of layer 7 complete; quic_7.ivy ready for verify."
- "Coverage SOUND for RFC 9000 §17.2."

If the claim cannot be stated in one sentence, the underlying work is not yet bounded enough to claim.

## Step 2 — RUN

Run the tool whose output grounds the claim. Each claim type has a canonical tool:

| Claim type | Canonical tool |
|---|---|
| "verification passed" | `ivy_verify(relative_path=<path>)` |
| "build done" | `ivy_diagnostics(mode="structural", relative_path=<path>)` returning no ERRORs |
| "coverage SOUND" | `ivy_coverage(test_file=<path>)` |
| "quality SOUND" | `ivy_quality(mode="suggestions"\|"gate", relative_path=<path>)` |
| "triage repaired" | `ivy_status(mode="health")` returning all subsystems healthy and no `staging_health` warnings |

The tool result must be from the current turn (no stale references).

## Step 3 — READ

Read the tool's output in full. Do not skim; do not infer success from a single field.

## Step 4 — VERIFY

Cross-check the result against (each check fails ⇒ halt):

1. The corresponding iron law (e.g., `NO_FIX_WITHOUT_VERIFY` for verify claims).
2. Any open `[GAP: #NN]` markers at the cited file:line locations.
3. The staleness rule: any file in the include closure edited since the tool was invoked this turn.

If any check fails, the claim is invalid. Halt and either re-run the tool or address the gap.

## Step 5 — THEN-claim

Only after Steps 1–4 have all passed do you emit the claim text to the user. Cite the tool result by tool invocation from the current turn:

> "Verification passed on bgp_connection.ivy (ivy_verify, current turn, status: OK)."

A claim without a cited current-turn tool result is unsupported and trips `STALENESS_RULE`.
