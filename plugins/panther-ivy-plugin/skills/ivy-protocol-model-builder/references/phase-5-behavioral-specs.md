# Phase 5: Behavioral Specs

## Purpose

Translate RFC requirements into machine-checkable constraints. This is the heart of the formal model.

## Ivy Concepts Taught

- **`around`/`before`/`after` advice**: Attach preconditions, postconditions, and state updates to actions declared elsewhere.
- **`require` statements**: `require expr` fails the test if `expr` is false. Each maps to an RFC MUST/SHALL.
- **`_generating` predicate**: Built-in boolean. `true` when Ivy runtime generates events (tester role), `false` when observing events from the IUT.
- **`~` as "not"**: `~_generating` means "not generating" (observing IUT events).
- **Role inversion**: Testing a server means Ivy acts as a client. The test file for server testing includes the **client** shim and **client** behavior, not the server shim. `ivy_{proto}_{tested_role}_behavior.ivy` constrains the tester's opposite role.
- **Multiple `around` blocks**: A single file can have multiple `around` blocks for different actions. The QUIC model's `quic_packet.ivy` has four: `around packet_event` (line 405, ~325 lines), `around send_ack_eliciting_handshake_packet` (line 735), `around send_ack_eliciting_application_packet` (line 974), `around send_ack_eliciting_initial_packet` (line 1218). For protocols with multiple message types or sub-events, plan for one `around` block per major event.
- **The dual-role specification pattern**:
  ```ivy
  around message_event(src, dst, msg) {
      if _generating {
          # Constraints on tester-generated traffic (ensure validity)
      };
      # Universal constraints (RFC requirements for all senders)
      require msg.length > 0;  # [rfcNNNN:X.Y] messages MUST NOT be empty
      if ~_generating {
          # Constraints on IUT traffic (spec violations = test failures)
      };
      ...  # original action body runs here (three literal dots)
      # State updates (apply to all events)
      message_seen(msg.id) := true;
  }
  ```

## QUIC Model References

- Main event spec: `quic_packet.ivy:405-729` — `around packet_event` with ~325 lines of `require` statements, `_generating` guards, and state updates
- Behavioral constraints: `ivy_quic_server_behavior.ivy` — `before frame.stream.handle` with `_generating` guards constraining tester's stream usage
- Frame handlers: `quic_frame.ivy` — sub-actions with `before` advice for frame-level constraints

## Requirement Extraction Process

1. Identify every MUST/SHALL/MUST NOT statement in the protocol spec.
2. For each, determine: universal (all senders), tester-only (`_generating`), or IUT-only (`~_generating`).
3. Translate to `require` with appropriate guards.
4. Add RFC bracket tag as comment: `# [rfcNNNN:X.Y]`

## Adaptation by Protocol Shape

| Shape | Behavioral Spec Pattern |
|---|---|
| Request-response | Simpler `_generating` guards: tester generates requests, checks responses |
| Stateless | Minimal inter-event state, mostly message-level validity checks |
| P2P symmetric | One behavioral spec for both roles, same constraints regardless |
| Complex state machine | Boolean relations per state per session, transition actions, FSM guards |

## Build Order

1. **Extract RFC requirements** — walk through spec, tag each MUST/SHALL as universal/tester/IUT.
2. **Main event specification** — `around` block for primary event, starting with 3-5 core requirements. Compile and test. Add incrementally.
3. **Sub-event specifications** — `before` advice on message-type handlers with `_generating` guards.
4. **Role-specific behavioral files** — one per tested role, constraining the tester's behavior.
5. **Integration test** — run against a real or known-good implementation. Verify pass/fail results.

## Debugging Failing Requirements

When a `require` fires, the test binary prints the source location:
```
FAIL: require at {proto}_message.ivy:42
```

Debugging methodology:
1. **Identify which `require`** — the line number points to the exact constraint.
2. **Add `import action show_*` for observability** — declare debug output actions and call them before the failing `require` to see the state. The QUIC model does this extensively (e.g., `import action show_queued_frames(scid:cid, frames:frame.arr)` in `quic_packet.ivy:402`).
3. **Bisect by commenting out requirements** — temporarily comment out groups of `require` statements to isolate which constraint is too strict or which state is wrong.
4. **Check `_generating` guards** — a common bug is a `require` that should be guarded by `_generating` but is not, causing it to fire on IUT events that do not need that constraint.

## Common Failure Modes

- **Test never progresses** (e.g., handshake never completes): Missing `export` or action weight too low.
- **Test always fails immediately**: `require` too strict — the IUT does something valid that the model rejects. Add `import action show_*` to inspect state.
- **Test always passes**: `require` too loose or `_finalize` does not check enough.
- **Test fails nondeterministically**: The random exploration sometimes takes paths that reveal real bugs and sometimes does not. Increase `test_iters` or add action weights.

For monitor patterns and specification best practices, consult the `specification-patterns` skill.

## Checkpoint

Run the compiled binary against a real implementation:
```bash
./{proto}_{role}_test seed=42 test_iters=100 server_addr=... client_addr=...
```
The test should produce event traces on stdout and terminate with either normal completion (pass) or a `require` failure (fail with line number).

To distinguish model bugs from real spec violations: if a test fails on a known-good implementation, the model is too strict (fix the `require`). If it passes on a known-buggy implementation, the model is too loose (add `require` constraints).

Use `ivy_coverage(mode="gaps")` to find uncovered RFC requirements and `ivy_coverage(mode="matrix")` for requirement-to-assertion mapping.

---

**STOP.** Present pass/fail results to the user. Do NOT proceed until user confirms the requirement-to-`require` mapping.
