# ivy_verdict -- Verdict Block Renderer

Renders a verdict block for adversarial quality gates (G1–G5). Unlike the other tool-renderers in this directory, `ivy_verdict` is not an MCP tool — it is a synthesized block written by the gate PostToolUse hooks (`assess-modeling.py`, `assess-testspec.py`, `assess-trace.py`, and `record-workflow-error.py` for the G4 verification gate). G1 (build exploration) is dispatched inline by the scaffold-ops skill rather than from a hook. The hooks read this spec to produce consistent output across gates.

## Input fields

The gate hook provides:

- `gate` — one of `g1` | `g2` | `g3` | `g4` | `g5`.
- `verdict` — one of `SOUND` | `UNSOUND` | `ABSTAIN`.
- `vote` — object `{sound: int, unsound: int, unsure: int}`.
- `tier` — one of `haiku` | `sonnet` | `opus`.
- `duration_s` — float, wall-clock of the fan-out.
- `patterns` — list of `{id: "#NN", file: str, line: int, reason: str}` (empty on `SOUND`).
- `abstain_reason` — string, present only when `verdict == "ABSTAIN"`.

## Default (no workflow active)

```
## Gate verdict — {gate} ({verdict})

Vote: {vote.sound} SOUND / {vote.unsound} UNSOUND / {vote.unsure} UNSURE ({tier} × {critic_count}, {duration_s}s)
{if verdict == "UNSOUND"}
Patterns cited:
{for p in patterns}
- [F-{index}] {p.id} at {p.file}:{p.line} — {p.reason}
{/for}
Markers written: {len(patterns)}
{elif verdict == "ABSTAIN"}
Abstention reason: {abstain_reason}
{/if}
```

## verify

- `SOUND`: single line — "G4 verification: SOUND ({vote.sound}/{total} critics, {tier}, {duration_s}s)".
- `UNSOUND`: numbered finding list using `F-NNN` IDs; each finding has pattern ID, `{file}:{line}`, and one-line reason; end with "See `.panther-ivy/workflow-journal.yaml` for full critic transcripts."
- `ABSTAIN`: single block — "G4 verification: ABSTAIN — {abstain_reason}. No `[GAP:]` markers written. Diagnosis required before proceeding." Fits after "Failure Details" in the overlay.

## build

- `SOUND`: per-gate confirmation — "{gate} gate: SOUND. Continue to next layer." Keep terse; build prose is dense enough already.
- `UNSOUND`: "{gate} gate: UNSOUND. Markers written at:" followed by bulleted `{file}:{line}` list. Follow with "Fix listed sites before proceeding." — the iron law applies.
- `ABSTAIN`: "{gate} gate: ABSTAIN — {abstain_reason}. Review the workflow journal before deciding." Place after "Current Layer".

## review

- Full finding table — | F-ID | Gate | Pattern | File:Line | Reason |.
- Group by gate; `UNSOUND` first, then `ABSTAIN`, then `SOUND` (summary count only).
- This mode is used when someone requests a retrospective audit of all gate verdicts for a session.

## triage

- One-line summary — "Gates: {sound_count} sound / {unsound_count} unsound / {abstain_count} abstain over last session."
- No finding detail. Point to `verify` or `review` workflow for details.

## Self-review block (only on analysis-heavy verdicts)

Append a `## Considerations` block per the `.claude/rules/ivy-formatting.md` convention when:

- `verdict == "ABSTAIN"` (the user needs to judge whether to escalate, defer, or accept).
- `verdict == "UNSOUND"` and pattern count ≥ 3 (multiple independent findings warrant discussing trade-offs).

Skip the self-review block on `SOUND` and on single-pattern `UNSOUND` — those cases are factual and don't need pro/con framing.

## Integration with GAP markers

The hook writes `[GAP: #NN <reason>]` markers inline at the cited `{file}:{line}` locations using `Edit`. The verdict block's finding list is a summary; the inline markers are the contract. The block and the markers must stay in sync: every finding in the block corresponds to exactly one marker, and vice versa. Promotion to `// DEFERRED YYYY-MM-DD: …` by the user removes the GAP marker but leaves the historical finding in the journal.
