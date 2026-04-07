# Phase 6: Test Scenarios

## Purpose

Create top-level test files that compose everything into runnable test cases.

## Ivy Concepts Taught

- **`export` declarations**: Tell the Ivy runtime which actions to randomly invoke during testing.
- **Action weights**: `attribute action.weight = "5"` biases random exploration (higher = more frequent).
- **`_finalize`**: Special action called by the Ivy runtime when test iterations are exhausted. Used for end-of-test assertions. Without it, a test that exchanged zero messages would still pass.
- **Test file structure**: includes + `after init` socket setup + exports + `_finalize`.

## QUIC Model References

- Basic test: `quic_tests/server_tests/quic_server_test.ivy` — 72 lines: includes, exports, init, finalize
- Feature test: `quic_tests/server_tests/quic_server_test_0rtt.ivy` — adds 0-RTT exports and config
- Error test: `quic_tests/server_tests/quic_server_test_tp_error.ivy` — intentionally invalid transport parameters
- Attack test: `quic_tests/mim_tests/quic_mim_test_forward.ivy` — includes MiM shim, exports forwarding actions

## Role Inversion in Test Files

Critical: a test targeting a server includes the **client** shim and **client** behavior, because Ivy acts as the opposite role. From `quic_server_test.ivy`:
```ivy
#lang ivy1.7
include ivy_quic_shim_client        # NOT shim_server — Ivy acts as client
include ivy_quic_client_behavior    # NOT server_behavior
include ivy_quic_client_standard_tp # Client transport parameters
```

## Test Scenario Taxonomy

### Category 1: Basic Conformance

Minimum viable test per role. Standard behavioral spec, standard config, core action exports.

```ivy
#lang ivy1.7
include order
include {proto}_infer              # inference engine (if applicable)
include file
include ivy_{proto}_shim_{opposite_role}   # Role inversion!
include {proto}_locale
include ivy_{proto}_{opposite_role}_behavior
include ivy_{proto}_{opposite_role}_standard_config

after init {
    sock := net.open(endpoint_id.{opposite_role}, {opposite_role}.ep);
    {opposite_role}.set_tls_id(0);  # if crypto
    {tested_role}.set_tls_id(1);    # if crypto
}

export message_event
export {sub_event_handles}

export action _finalize = {
    require {meaningful_exchange_happened};
}
```

### Category 2: Feature-Specific

Small deltas from basic test: add an export, swap a config, add a `before` constraint. One per protocol feature of interest.

### Category 3: Error Handling

Intentionally invalid configs or messages. `_finalize` asserts specific error was produced. Tests that IUT correctly rejects invalid input.

### Category 4: Attack Tests (Conditional)

Requires:
1. **Forged message type** in `{proto}_attacks_stack/` — same struct as normal message but with relaxed constraints (e.g., raw `protected_payload` instead of decoded fields).
2. **Attack actions** — `forged_message_event`, `replay_message_event`, `forward_to_{role}_event`. Each has `around` advice enforcing attacker capabilities.
3. **Attacker entity** — MiM (two sockets, configurable forwarding/replay/modification booleans) or direct attacker (single socket).
4. **Attack test file** — includes both normal shim and attack shim, exports both normal and attack actions.

QUIC reference: `quic_attacks_stack/forged_quic_packet.ivy` defines forged packet types. `quic_entities/ivy_quic_mim.ivy` defines MiM entity with `is_mim`, `forward_packets`, `modify_packets`, `replay_packets` booleans. `quic_tests/mim_tests/quic_mim_test_forward.ivy` exports `forward_packet_to_client_event` and `forward_packet_to_server_event` alongside normal protocol actions.

## Build Order

1. **Basic conformance test per role** — write, compile, run. Tune weights until test reaches meaningful states.
2. **Feature-specific tests** — one at a time, incremental deltas from basic test.
3. **Error handling tests** — invalid configs, verify IUT rejects them.
4. **Attack tests** — build attack stack, create attacker entities, write test files.

For NCT/NACT test design methodology, consult the `nct-methodology` or `nact-methodology` skill.

## Checkpoint

Run the full test suite:
```bash
for test in {proto}_tests/**/*.ivy; do
    ivyc target=test test_iters=100 "$test"
    ./$(basename "$test" .ivy) seed=42 server_addr=... client_addr=...
done
```

Or use `ivy_compile` and `ivy_patterns(mode="check")` MCP tools for structured verification.

To distinguish model bugs from real spec violations: if a test fails on a known-good implementation, the model is too strict (fix the `require`). If it passes on a known-buggy implementation, the model is too loose (add `require` constraints).

---

**STOP.** Present full test suite results to the user. Congratulations on completing the formal protocol model! User reviews pass/fail and confirms the model is complete.
