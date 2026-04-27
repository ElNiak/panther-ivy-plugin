# Walkthrough — NCT path for a QUIC server IUT

A concrete end-to-end walkthrough showing how the NCT methodology drives
`workflow-build` + `workflow-verify` from RFC selection to a SOUND model
with IUT testing. The example assumes a fresh workspace and an IUT that
implements the protocol.

## Goal

Test an FRR-Picoquic QUIC server against RFC 9000 §17.2 (long header
packets) and §19.6 (CRYPTO frame) compliance.

## Step 1 — Workspace setup

```text
/set-workspace quic
```

The hook chain writes `IVY_ACTIVE_WORKSPACE=quic` to `$CLAUDE_ENV_FILE`.
The PreToolUse `check-workspace-scope.py` hook now blocks any
`Write`/`Edit` outside `protocol-testing/quic/`. Reads across protocols
remain free.

## Step 2 — Routing

User prompt: *"create a QUIC server compliance model from RFC 9000 §17"*.

The UserPromptSubmit hook reads `routing-rules.json`, scores
`workflow-build` highest (matches `intentPatterns`: `(create|build).*?model`,
`RFC\s*\d+.*model`), and emits:

```text
[ROUTING] Activate the 'workflow-build' workflow skill.
```

## Step 3 — Build Phase 1 (Methodology detection)

`workflow-build` reads RFC 9000 keywords, finds no `attack` / `attacker`
keywords, no `network simulation` mentions, classifies `methodology=nct`,
and writes `build-state.yaml`:

```yaml
methodology: nct
target_protocol: quic
rfc_source: rfc9000
target_role: server
iut_layer: picoquic
```

## Step 4 — Build Phase 2 (Blueprint)

Loads `Skill(panther-ivy-plugin:knowledge-specification-patterns)` and
applies the 14-layer template. For QUIC server NCT the relevant subset:

| Layer | File | Status |
|---|---|---|
| 1 — Types | `quic_stack/quic_types.ivy` | exists |
| 2 — Network | `quic_stack/quic_packet.ivy` | exists |
| 3 — Frame | `quic_stack/quic_frame.ivy` | exists |
| 4 — Connection | `quic_stack/quic_connection.ivy` | exists |
| 7 — Test spec | `quic_tests/server_tests/quic_server_test_handshake.ivy` | NEW |

`build-state.yaml.layers` records each layer's status; only layer 7 will
be authored in this run.

## Step 5 — Build Phase 3 (Implement layer 7)

Iron law `NO_LAYER_WITHOUT_SCAFFOLD` binds: before writing
`quic_server_test_handshake.ivy`, run
`ivy_diagnostics(mode="structural")` on the predecessor stack
(layers 1-4). All return SOUND. Layer 7 is authored.

PostToolUse hooks fire on the Write:
- `post-write-ivy-lint.sh` — fast structural check (passes).
- `assess-testspec.py` — G3 test-spec gate dispatches 3 critics; verdict
  SOUND.

The role-inversion rule applies: testing a QUIC *server* means Ivy plays
the *client* (`quic_server_test_*` files contain client-side
test-traffic generators).

## Step 6 — Build Phase 4 (Hand off to verify)

`append_pending_dispatch(verify, reason="build Phase 4 — post-modeling
verification")`, clear `active-workflow`, end turn.

## Step 7 — Verify cycle (next turn)

UserPromptSubmit hook reads the journal, finds the fresh
`pending_dispatch`, emits `[ROUTING:CONTINUE]` for `workflow-verify`,
and `workflow-navigate` Phase 1 Step 2c consumes the entry and invokes
`Skill(workflow-verify)`. Verify Phase 3 (compile) → Phase 4 (verify)
runs; G4 critic confirms SOUND with calibrated 3-of-3 vote.

## Step 8 — Verify Phase 5 (IUT testing)

Phase 5 dispatches `ivy_iut_test(protocol="quic",
test_name="quic_server_test_handshake", iut_name="picoquic")`. The
G5 trace-analysis gate (PostToolUse) reads results.json → tester log →
IUT log → pcap, applying catalog patterns `#100-107` + `#500-559`.
Catalog `#501` (Ivy trace claims event, pcap shows nothing) is the
primary check; `#505` (model bug misattributed to IUT) is the
asymmetry check. Verdict SOUND.

## Step 9 — Hand back to build (quality gate)

Verify Phase 6 emits
`append_pending_dispatch(build, phase_hint="quality-gate")`. Build
re-activates at Phase 5 next turn, dispatches `model-reviewer` and
`traceability-agent` in parallel, surfaces ERROR/WARNING/INFO findings
per `.claude/rules/ivy-formatting.md` severity.

## What this walkthrough exercised

| Concept | Where |
|---|---|
| `/set-workspace` edit isolation | Step 1 |
| `routing-rules.json` regex match | Step 2 |
| `build-state.yaml` methodology field | Step 3 |
| 14-layer template selection | Step 4 |
| Iron law `NO_LAYER_WITHOUT_SCAFFOLD` | Step 5 |
| Role inversion (Ivy plays client when testing a server) | Step 5 |
| G3 test-spec adversarial gate | Step 5 |
| `pending_dispatch` async hand-off | Steps 6, 9 |
| G4 verification gate | Step 7 |
| G5 trace-analysis gate (catalog `#501`, `#505`) | Step 8 |
| Phase 5 quality gate (model-reviewer + traceability-agent) | Step 9 |
