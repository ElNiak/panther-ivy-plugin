# Worked example — QUIC handshake verification (FAIL → SOUND)

A full end-to-end walkthrough of one verify cycle: compile, fail, inline counterexample interpretation, fix, re-verify, completion-gate. The example is illustrative — the exact JSON shapes and trace formats may evolve with the verifier; refresh this page whenever a verifier-pattern is added to `skills/verification-failures/references/verifier_patterns.md`.

## Setup

- Workspace: `quic` (active via `/set-workspace quic`).
- Target spec: `protocol-testing/quic/quic_tests/server_tests/quic_server_test_handshake.ivy`.
- IUT: `picoquic` (selected at Phase 5 step 2).
- Methodology: NCT.

## Phase 3 — Compile (success)

```text
ivy_compile(relative_path="protocol-testing/quic/quic_tests/server_tests/quic_server_test_handshake.ivy")
→ {"status": "OK", "binary": "/tmp/ivy-build/quic_server_test_handshake",
   "duration_seconds": 18.4}
```

The structural-check + Ivy → C++ compile completed in 18 s. Phase 3 advances.

## Phase 4 — Verify (FAIL with counterexample)

```text
ivy_verify(relative_path="protocol-testing/quic/quic_tests/server_tests/quic_server_test_handshake.ivy")
→ {
    "status": "FAIL",
    "started_at": "2026-04-27T09:14:02Z",
    "duration_seconds": 41.7,
    "counterexample": {
      "assertion": "conn_seen(C)",
      "assertion_line": 142,
      "steps": [
        {"action": "quic_packet.handle", "vars": {"conn_seen(0x4c)": "false", "scid": "0x4c"}},
        {"action": "frame.crypto.handle", "vars": {"conn_seen(0x4c)": "false", "data_len": "528"}}
      ]
    },
    "counterexample_trace": "Violated assertion (Line 142):\n  require conn_seen(C)\nExecution trace (2 steps):\n  Step 1: quic_packet.handle\n    conn_seen(0x4c) = false\n    scid = 0x4c\n  Step 2: frame.crypto.handle\n    conn_seen(0x4c) = false\n    data_len = 528"
  }
```

The verifier agent dispatches G4 inline (three context-isolated `g-fidelity-critic` agents in parallel via `cross-cutting-parallel-dispatch`). They cite verifier-pattern catalog `#410` (missing guard) — the trace shows `frame.crypto.handle` firing while `conn_seen(scid)` is still `false`, meaning a precondition is missing on the `before` block. Verdict: `UNSOUND(#410, missing-guard, quic_server_test_handshake.ivy:142)`.

## Phase 6 — Diagnose (inline counterexample interpretation)

Verify-ops Phase 6 owns counterexample interpretation in-place because `verification-failures` is preloaded at agent spawn. The verifier agent walks the trace step-by-step and matches against the catalog:

```text
Diagnosis (inline against verification-failures catalog):
  Pattern: Missing guard (catalog #410).
  Site: protocol-testing/quic/quic_tests/server_tests/quic_server_test_handshake.ivy:140
        before frame.crypto.handle(f:frame.crypto, scid:cid, dcid:cid)
  Root cause: the `before frame.crypto.handle` block lacks
              `require initial_received(scid)`. Without this guard, the
              solver finds a path where a CRYPTO frame is processed before
              the matching Initial packet has been seen, leaving
              `conn_seen(scid) = false`.
  Proposed fix:
    @@ -139,3 +139,4 @@
       before frame.crypto.handle(f:frame.crypto, scid:cid, dcid:cid) {
    +    require initial_received(scid);
         require ~conn_closed(scid);
         require crypto_offset(scid) = f.offset;
       }
```

This is an inline interpretation by the verifier agent — no separate diagnostic-agent dispatch. MPE was not needed because catalog `#410` matched cleanly on the first walk.

## Phase 7 — Fix (apply diff)

Attempt counter is at 0 (first fix on this file this session), well below the cap of 3. The verifier appends `progress{kind: "fix_attempt", key: "quic_server_test_handshake.ivy", attempt: 1}` and applies the unified diff via the `Edit` tool. The PostToolUse `posttooluse/gates/run-gate.py --id g2` hook does NOT fire G2 on Phase 7 verify-time edits (G2 is scaffold-time only — see `cross-cutting-reflection-patterns/references/gates.md` § "G2/G3 workflow scope").

## Phase 4 — Re-verify (SOUND)

`NO_FIX_WITHOUT_VERIFY` binds: the claim of resolution is not licensed until a fresh `ivy_verify` returns OK on the edited spec.

```text
ivy_verify(relative_path="protocol-testing/quic/quic_tests/server_tests/quic_server_test_handshake.ivy")
→ {"status": "OK", "started_at": "2026-04-27T09:18:36Z",
   "duration_seconds": 39.9}
```

G4 critics re-dispatch on the new tool result. Verdict: `SOUND` (3-of-3 vote).

## Completion gate

Invoke `Skill(skill="panther-ivy-plugin:ivy")` and read `references/completion-gate.md` for the 5-step IDENTIFY → RUN → READ → VERIFY → THEN-claim sequence. With the fresh OK + SOUND verdict + the journal showing the fix and re-verify in the same turn, the gate passes. The user-facing "verification passed" claim is now licensed.

## What this example exercised

| Concept | Where it appeared |
|---|---|
| Iron law `NO_FIX_WITHOUT_VERIFY` | Re-verify at Phase 4 before the SOUND claim. |
| Inline G4 dispatch (verifier-owned, not hook-deferred) | Three `g-fidelity-critic` agents at Phase 4 in the same turn. |
| Inline counterexample interpretation | Phase 6 catalog walk with no separate diagnostic-agent dispatch. |
| Counterexample interpretation pattern `#410` | Cited by both G4 verdict and Phase 6 diagnosis. |
| Phase 7 attempt-counter accountability | `progress{kind: "fix_attempt", attempt: 1}` journal event. |
| `cross-cutting-completion-gate` | Final IDENTIFY → THEN-claim. |
| G2/G3 workflow-scope rule | Phase 7 fix did NOT fire G2 (scaffold-time only). |

Refresh trigger: when a new verifier-pattern is added to `verification-failures/references/verifier_patterns.md`, re-derive the JSON / trace format here so the example stays representative of current verifier output.
