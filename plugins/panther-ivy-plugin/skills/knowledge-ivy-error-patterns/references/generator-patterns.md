# Generator patterns

Protocol test generators (Ivy's `_generating` mode plus exported actions) need careful design to ensure the SMT solver's random action selection actually produces wire traffic. This reference captures the anti-patterns and the correct patterns.

## Generator starvation (test passes but no protocol traffic)

**Trigger:** Test completes with PASS verdict but pcap shows few or no protocol messages. Alternatively, the IUT's hold timer expires or the connection drops mid-test despite no verification failure.

**Symptom:** High iteration count (e.g., 1000+) with disproportionately few messages in the pcap (fewer than 5). The generator spends most iterations on non-message actions (timers, internal state transitions) and rarely selects message-producing actions.

**Root Cause:** One or more of:

- **Timer competition**: Exported timer events (e.g., `timeout_event`) consume generator iterations without producing wire traffic. The generator picks timer actions because they have fewer `require` guards.
- **Two-step message patterns**: Message construction split across two exported actions (e.g., `create_msg` + `send_msg`). The generator must pick both in sequence, but random selection makes this unlikely.
- **Missing handle exports**: Sub-element builder actions (e.g., `frame.path_attribute.handle`) are not exported, so the generator cannot construct composite messages.
- **Over-constrained `before` guards**: `require` clauses on message actions reject most generated inputs, causing the generator to fall back to simpler actions.

**Correct Pattern:**

1. Apply the auto-send pattern: merge message construction and sending into a single exported action so every selection produces a wire message.
2. Remove timer event exports (`timeout_event`, `keepalive_timer`) from the test file. Handle timers internally via `after init` or shim callbacks.
3. Export handle actions for composite message sub-elements, guarded by `_generating`:
   ```ivy
   export frame.path_attribute.handle
   before frame.path_attribute.handle(f:frame.path_attribute, ...) {
       if _generating { require connected(the_cid); }
   }
   ```
4. Simplify `before` guards on message actions to reduce rejection rate.

**Diagnosis:** Run wire validation after IUT test (see `verify` workflow, Post-IUT Wire Validation). Use tshark to count messages per direction and compare against iteration count.

**Related:** ivy-writing-guide skill (load via `Skill(skill="panther-ivy-plugin:knowledge-ivy-writing-guide")`), generator-mechanics reference; `verify` workflow > Post-IUT Wire Validation.
