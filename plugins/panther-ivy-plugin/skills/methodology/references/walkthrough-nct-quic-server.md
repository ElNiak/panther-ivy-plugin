# Walkthrough — NCT path for a QUIC server IUT

A concrete end-to-end walkthrough showing how the NCT methodology drives
the `scaffold` + `refine` + `experiment` workflows from RFC selection to a
SOUND model with IUT testing. The example assumes a fresh workspace and an
IUT that implements the protocol.

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

The orchestrator skill `panther-ivy-plugin:ivy` classifies the intent
("create / build a model") and routes to the scaffold workflow per its
Dispatch table. The post-Phase-E orchestrator replaces the pre-Phase-C
`route-user-prompt.py` hook + `routing-rules.json` regex matcher; the
semantics (intent → workflow target) survive but the surface is now a
prose dispatch table in `skills/ivy/SKILL.md` rather than a JSON file.

## Step 3 — Scaffold Phase 1 (Methodology detection)

`scaffold` workflow reads RFC 9000 keywords, finds no `attack` / `attacker`
keywords, no `network simulation` mentions, classifies `methodology=nct`,
and writes `scaffold-state.yaml`:

```yaml
methodology: nct
target_protocol: quic
rfc_source: rfc9000
target_role: server
iut_layer: picoquic
```

## Step 4 — Scaffold Phase 2 (Blueprint)

Loads `Skill(panther-ivy-plugin:specification-patterns)` and
applies the 14-layer template. For QUIC server NCT the relevant subset:

| Layer | File | Status |
|---|---|---|
| 1 — Types | `quic_stack/quic_types.ivy` | exists |
| 2 — Network | `quic_stack/quic_packet.ivy` | exists |
| 3 — Frame | `quic_stack/quic_frame.ivy` | exists |
| 4 — Connection | `quic_stack/quic_connection.ivy` | exists |
| 7 — Test spec | `quic_tests/server_tests/quic_server_test_handshake.ivy` | NEW |

`scaffold-state.yaml.layers` records each layer's status; only layer 7 will
be authored in this run.

## Step 5 — Scaffold Phase 3 (Implement layer 7)

Iron law `NO_LAYER_WITHOUT_SCAFFOLD` binds: before writing
`quic_server_test_handshake.ivy`, run
`ivy_diagnostics(mode="structural")` on the predecessor stack
(layers 1-4). All return SOUND. Layer 7 is authored.

PostToolUse hooks fire on the Write:
- `post-write-ivy-lint.py` — fast structural check (passes).
- `assess-testspec.py` — G3 test-spec gate dispatches 3 critics; verdict
  SOUND.

The role-inversion rule applies: testing a QUIC *server* means Ivy plays
the *client* (`quic_server_test_*` files contain client-side
test-traffic generators).

## Step 6 — Scaffold Phase 4 (Hand off to verify)

`append_pending_dispatch(verify, reason="scaffold Phase 4 — post-modeling
verification")`, clear `active-workflow`, end turn.

## Step 7 — Verify cycle (next turn)

The orchestrator skill `panther-ivy-plugin:ivy` Phase 1.5 (resume hand-off)
reads the journal, finds the fresh `pending_dispatch`, writes a
`workflow_resumed` event, sets the active-workflow YAML, and dispatches
`ivy-refiner-agent` per the contract §4 consume-pair semantics.
Refine Phase 3 (compile) → Phase 4 (verify) runs; G4 critic confirms
SOUND with calibrated 3-of-3 vote.

## Step 8 — Experiment (IUT testing)

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
re-activates at Phase 5 next turn, dispatches `ivy-reviewer-agent` and
`traceability-agent` in parallel, surfaces ERROR/WARNING/INFO findings
per `.claude/rules/ivy-formatting.md` severity.

## What this walkthrough exercised

| Concept | Where |
|---|---|
| `/set-workspace` edit isolation | Step 1 |
| Orchestrator dispatch-table intent classification | Step 2 |
| `scaffold-state.yaml` methodology field | Step 3 |
| 14-layer template selection | Step 4 |
| Iron law `NO_LAYER_WITHOUT_SCAFFOLD` | Step 5 |
| Role inversion (Ivy plays client when testing a server) | Step 5 |
| G3 test-spec adversarial gate | Step 5 |
| `pending_dispatch` async hand-off | Steps 6, 9 |
| G4 verification gate | Step 7 |
| G5 trace-analysis gate (catalog `#501`, `#505`) | Step 8 |
| Phase 5 quality gate (ivy-reviewer-agent + traceability-agent) | Step 9 |
