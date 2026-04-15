# Ivy Error Patterns — Full Lookup Table

Complete error-to-fix reference. Each entry maps a cryptic Ivy error to its root cause, correct pattern, and working examples.

---

## 1. `'<name>' not found` on relation/function declaration

**Trigger:** Using a parameter name that collides with an existing symbol or is parsed as an unresolved reference.

```ivy
# WRONG — Ivy resolves 'src' as a symbol reference, not a fresh binder
relation update_processed(src:bgp_id, dst:bgp_id)
# Error: 'src' not found
```

**Root Cause:** In Ivy, the token before `:` in a parameter list is resolved as a symbol in the current scope. If `src` exists as a declared object, type, or individual, it binds to that instead of being treated as a fresh parameter name. If `src` does not exist at all, Ivy reports `'src' not found` because it tried to resolve it as a reference.

**Correct Pattern:** Use single uppercase letter parameter names that are unambiguous fresh binders:

```ivy
# RIGHT — conventional single-letter parameter names
relation update_processed(S:bgp_id, D:bgp_id)
```

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:229` — `relation conn_seen(C:cid)`
- `protocol-testing/bgp/bgp_shims/bgp_shim.ivy:41` — `relation isup(A:ip.addr)`

**Related:** `ivy-writing-guide` skill > Relations section

---

## 2. `ungrounded variable X in relation`

**Trigger:** Free variable in a relation expression not bound by a quantifier or the head of a rule.

**Root Cause:** All variables in relation expressions must be bound. A variable that appears in the body but not in the head and not under a quantifier is "ungrounded."

**Correct Pattern:** Bind with explicit quantifiers or ensure variables appear in the head:

```ivy
# WRONG — X is free
invariant recv(X,Y) -> sent(X,Y)

# RIGHT — X and Y are implicitly universally quantified (this is fine for invariants)
# But in action bodies or requires, use explicit quantifiers:
require exists S. req(other, S, self);
```

**Working Examples:**
- `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56` — `require exists S. req(other,S,self);`

**Related:** `ivy-writing-guide` skill > Invariants section

---

## 3. `invariant ... failed` / `failed to verify invariant preservation`

**Trigger:** An action modifies state in a way that violates a declared invariant.

**Root Cause:** One of:
- Missing state update (a relation is modified but a dependent relation is not updated)
- Missing precondition (the action is called in a state where the invariant cannot be maintained)
- Invariant too strong (it cannot be maintained by any correct action sequence)

**Correct Pattern:**
1. Check all modified relations are updated consistently
2. Add `require` guards to actions
3. Verify `after init` blocks set initial state compatible with the invariant

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init` block initializing all relations
- `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56-70` — `require` guards on actions

**Related:** `ivy-writing-guide` skill > Invariants, Actions sections

---

## 4. `assumption failed` (isolate assumption violation)

**Trigger:** An isolate's assumptions about another isolate's behavior are not satisfied.

**Root Cause:** The specification of the assumed isolate does not guarantee what the assuming isolate expects.

**Correct Pattern:**
1. Run `ivy_model_info` to list all isolates
2. Check each isolate's assumptions against its specification
3. Strengthen the assumed isolate's specification, or weaken the assumption

**Working Examples:** Search for `object` and `specification` blocks in the protocol family.

**Related:** `ivy-writing-guide` skill > Isolates section

---

## 5. `type mismatch` / `type error`

**Trigger:** Incompatible types in an expression (e.g., using `nat` where `packet_type` is expected).

**Root Cause:** Ivy's type system is strict with no implicit coercions.

**Correct Pattern:** Ensure all variables and expressions have consistent types. Check type declarations.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:226` — `function initial_max_stream_data_uni_server_0rtt : stream_pos`

**Related:** `ivy-writing-guide` skill > Type Declarations section

---

## 6. `circular dependency`

**Trigger:** Two or more modules or objects depend on each other via includes.

**Root Cause:** Ivy does not support circular include dependencies.

**Correct Pattern:** Structure files as a DAG. Introduce abstract interfaces to break cycles.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:3-5` — linear include chain: `include quic_types`, `include quic_transport_error_code`, `include quic_stream`
- `protocol-testing/bgp/bgp_utils/random_value.ivy:3` — single include: `include bgp_type`

**Related:** `ivy-writing-guide` skill > Include Directives section

---

## 7. `not well-founded`

**Trigger:** `definition ... not well-founded` during verification.

**Root Cause:** Ivy requires every recursive definition to be well-founded — the recursive call must be on a structurally smaller argument so termination can be proven. A definition that calls itself without a decreasing measure violates this requirement.

```ivy
# WRONG — count recurses on S without a decreasing measure
definition count(S:set) = ite(empty(S), 0, 1 + count(S))
# Error: definition count not well-founded
```

**Correct Pattern:** Either eliminate recursion by using Ivy's built-in aggregate operators, or provide an explicit termination measure using a `decreases` clause:

```ivy
# RIGHT — no recursion; express using relations and quantifiers
function count(S:set) : nat
axiom forall S. count(S) = card(S)

# RIGHT — recursion with explicit decreasing measure
definition count(S:set) decreases size(S) =
    ite(empty(S), 0, 1 + count(remove_min(S)))
```

**Related:** `ivy-writing-guide` skill > Definitions section

---

## 8. `uninterpreted sort has no instances`

**Trigger:** `uninterpreted sort <T> has no instances` during verification or model extraction.

**Root Cause:** A sort declared with `type T` is fully abstract — Ivy's model extractor requires at least one concrete member. Without axioms or an `individual` providing an element, Z3 cannot construct a finite model.

```ivy
# WRONG — abstract sort with no inhabitants
type connection_id
# Error: uninterpreted sort connection_id has no instances
```

**Correct Pattern:** Either enumerate values with `interpret`, declare at least one individual, or add an axiom asserting the sort is inhabited:

```ivy
# RIGHT — enumerate concrete values (preferred for small finite types)
type connection_id = {cid_a, cid_b, cid_c}

# RIGHT — declare a canonical individual so the sort is non-empty
type connection_id
individual default_cid : connection_id

# RIGHT — axiom asserting the sort is inhabited
type connection_id
axiom exists C:connection_id. true
```

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_types.ivy` — `type cid` defined with `interpret cid -> bv[8]`
- `protocol-testing/bgp/bgp_types/bgp_type.ivy` — `type bgp_id` with concrete enumeration

**Related:** `ivy-writing-guide` skill > Type Declarations section

---

## 9. Z3 timeout / `unknown`

**Trigger:** Verification takes too long; the SMT solver cannot decide.

**Root Cause:** Proof obligation too complex (deep quantifier nesting, large isolates, complex arithmetic).

**Correct Pattern:**
1. Break into smaller lemmas
2. Add ghost state or auxiliary invariants to guide the prover
3. Use `isolate` boundaries to limit what the solver must reason about
4. Reduce quantifier nesting depth

---

## 10. `multiple definitions`

**Trigger:** `<name> multiply defined` or `multiple definitions of <name>` during compilation or verification.

**Root Cause:** Two files in the include graph declare the same symbol (type, relation, function, or action) at the top level. Ivy does not allow redeclaration — even if both declarations are identical.

```ivy
# file_a.ivy
include bgp_type
type connection_state = {idle, active, established}

# file_b.ivy
include bgp_type
type connection_state = {idle, active, established}   # duplicate

# test.ivy
include file_a
include file_b
# Error: connection_state multiply defined
```

**Correct Pattern:**
1. Run `ivy_include_graph` to identify which two files both declare the symbol.
2. Move the shared declaration to a single common file and `include` that file from both.
3. If the two declarations differ in intent, namespace one inside an `object` to avoid collision.

```ivy
# RIGHT — declare once in a shared file (e.g., bgp_connection_state.ivy)
type connection_state = {idle, active, established}

# file_a.ivy — include the shared file
include bgp_connection_state

# file_b.ivy — include the same shared file (no redeclaration)
include bgp_connection_state
```

**Working Examples:**
- `protocol-testing/bgp/bgp_types/bgp_type.ivy` — canonical shared type declarations included by all BGP stack files
- `protocol-testing/quic/quic_stack/quic_types.ivy` — single source of truth for QUIC type definitions

**Related:** `ivy-writing-guide` skill > Module System section

---

## 11. `cannot find isolate X`

**Trigger:** Misspelled isolate name or missing declaration.

**Root Cause:** The isolate name in the command does not match any declaration in the file.

**Correct Pattern:**
1. Check spelling of the isolate name
2. Run `ivy_model_info` to list declared isolates

**Related:** `ivy-writing-guide` skill > Isolates section

---

## 12. Missing `after init` causing arbitrary initial values

**Trigger:** Invariant fails on initial state; relations have unexpected values.

**Root Cause:** Without `after init`, relations start with arbitrary (unconstrained) values.

**Correct Pattern:** Explicitly initialize all mutable relations in `after init` blocks:

```ivy
after init {
    conn_seen(C) := false;
    last_pkt_num(C,L) := 0;
    conn_closed(C) := false;
}
```

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init { conn_seen(C) := false; ... }`
- `protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy:10` — `after init {`

**Related:** `ivy-writing-guide` skill > Common Pitfalls > Forgetting `after init` blocks

---

## 13. Generator starvation (test passes but no protocol traffic)

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

**Related:** `generator-mechanics.md`, `verify` workflow > Post-IUT Wire Validation
