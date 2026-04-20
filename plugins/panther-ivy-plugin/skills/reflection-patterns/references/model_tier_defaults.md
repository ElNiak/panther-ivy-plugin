# Model Tier Defaults — Adversarial Quality Gates

Per-tier parameters for the context-isolated critic fan-out at each adversarial quality gate (G1 exploration, G2 per-layer modeling, G3 test-spec, G4 verification, G5 trace analysis). Owned by the `reflection-patterns` skill; loaded by the discipline-layer extension of MPE.

The orchestrator reads the active tier from the `CLAUDE_MODEL_TIER` environment variable (`haiku` | `sonnet` | `opus`). If unset, **default to Sonnet**.

## Tier table

| Tier | Critics per gate | Vote (confirm / refute) | Abstain after | Catalog sweep | Re-entry caps |
|---|---|---|---|---|---|
| Haiku | 7 | 5 / 3 | 3 revise failures | All entries in gate's ID range | G1: 1× per build; G2: 1× per `Write/Edit`; G3: 1×; G4: 1× per `ivy_verify`; G5: 1× per `ivy_iut_test` |
| Sonnet (default) | 5 | 4 / 2 | 3 revise failures | All entries in gate's ID range + methodology overlay | same as Haiku |
| Opus | 3 (G1, G5) / 5 (G2, G3, G4) | 4 / 2 (or 2 / 1 when N=3) | 5 revise failures | All entries + one dedicated critic per catalog pattern if Opus budget allows | same as Haiku |

## Per-gate defaults (for the discipline layer to read)

| Gate | Tier target | Critics | Confirm | Refute | Catalog slice |
|---|---|---|---|---|---|
| G1 exploration | Opus | 3 | 2 | 1 | #100-149 + (#150-199 if NACT) + #250-299 |
| G2 modeling | Sonnet | 5 | 4 | 2 | #200-249 + #250-299 + (#260-289 if NSCT) |
| G3 test-spec | Sonnet | 5 | 4 | 2 | #200-208 + #256-259 + #300-399 |
| G4 verification | Sonnet | 5 | 4 | 2 | #200-249 + #250-299 + #400-499 |
| G5 trace analysis | Sonnet | 5 | 4 | 2 | #100-107 + #500-559 + (#560-589 if NSCT) |

Opus tier for G1 and G5 reflects that these are high-leverage semantic checks run at most once per build or IUT run. G2/G3/G4 fire more frequently (per-file or per-verify); Sonnet × 5 keeps total latency bounded.

## Asymmetric-vote rationale

Our convention: **4 critics must return `SOUND` to confirm; 2 critics suffice to refute.** The asymmetry encodes a deliberate bias — one flaky critic must not be able to veto a correct result, but two independent dissents is a real signal worth acting on. At the Opus G1/G5 configuration of N=3, the ratios scale to 2-confirm / 1-refute (same intent: one dissent is real; two confirmations need a third independent voice).

## Pigeonhole early-exit

Our convention: **once `inflight >= confirm_needed + refute_needed - 1`, the remaining critics carry no decisional information regardless of how they vote. Do not spawn them.** This bounds gate latency without reducing decision quality.

Concretely, with Sonnet × 5 at 4-confirm / 2-refute:
- If the first 4 critics all return `SOUND`, do not spawn critic 5. Emit `VERDICT_SOUND` immediately.
- If the first 2 critics return `UNSOUND`, do not spawn critics 3-5. Emit `VERDICT_UNSOUND` immediately.
- If after 4 spawns the tally is 3 SOUND / 1 UNSOUND / 0 ABSTAIN, the 5th can still tip; spawn it.
- If after 5 spawns the tally is 3 SOUND / 1 UNSOUND / 1 ABSTAIN, no threshold is met; emit `VERDICT_ABSTAIN`.

## Revise-fail budget

After a gate emits `VERDICT_UNSOUND`, the workflow revises the artifact and re-runs the gate. The revise counter increments per cycle. If the counter exceeds the tier's revise-fail budget (Haiku/Sonnet: 3; Opus: 5) without reaching `VERDICT_SOUND`, the gate escalates to `VERDICT_ABSTAIN` with `abstain_reason: revise_budget_exhausted` and surfaces all pattern IDs that have fired across the cycles. The user must then decide: deeper investigation, methodology change, or explicit deferral via `// DEFERRED` promotion.

## Critic-isolation reminder (load-bearing)

This paragraph is embedded in every per-gate critic template to keep the isolation contract visible at the point of action.

> **Verify independently.** You have not seen — and must not imagine — what any other critic said about this artifact. Do not reason "this probably already got checked." Your verdict is the only verdict you control. If you wave something through on the assumption that another pass will catch it, and the other passes reason the same way, an unsound spec ships.

## Abstention contract (load-bearing)

Embedded in every per-gate critic template alongside the isolation reminder:

> **Do not guess.** A wrong confident verdict is worse than an honest `ABSTAIN`. The measure that matters is conditional accuracy — when you say `SOUND`, are you right?
>
> If your reasoning hits a wall, return `ABSTAIN` with a short reason. The orchestrator's voting rules handle it. Your job is not to close the gate; your job is to report what you genuinely saw.

## Changing tier defaults

- To change per-gate critic count or thresholds for a local run, set environment variables:
  - `PANTHER_IVY_GATE_TIER=opus` overrides the whole gate block.
  - `PANTHER_IVY_GATE_G2_CRITICS=7` overrides critics for G2 only.
  - `PANTHER_IVY_GATE_G4_CONFIRM=5` raises the confirm threshold for G4.
- Override env vars are read by the orchestrator at spawn time. The verbatim critic prompt is unchanged; only the fan-out parameters differ.
- Document any non-default in the run's journal so later audits know why a gate fired with different parameters than canonical defaults.

## When to use Haiku

Haiku's wider fan-out (7 × Haiku) often costs less than 5 × Sonnet and can surface catalog hits Sonnet missed at marginal cost. Use Haiku when:
- G2 is firing per-layer across a 14-layer build and aggregate latency matters more than per-gate depth.
- A trigger-eval shakedown needs many distinct dispatch probes.
- An initial catalog seed is being validated; wider sweep surfaces which patterns are load-bearing.

Do not use Haiku for G1 or G5. Both need semantic depth (blueprint reasoning; wire-trace correlation) that benefits from Opus.
