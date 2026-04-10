---
name: ivy-error-patterns
description: Use when encountering any Ivy error message to look up the root cause and correct fix. Lookup table mapping cryptic Ivy errors to causes, correct patterns, and working examples. Triggers on any Ivy error message including "not found", "ungrounded", "invariant failed", "assumption failed", "type mismatch", "type error", "circular dependency", "not well-founded", "no instances", "timeout", "unknown", "multiple definitions", "cannot find isolate".
---

# Ivy Error Patterns Reference

Lookup table for Ivy error messages. Each entry maps a cryptic error to its root cause and the correct fix, with pointers to working examples in `protocol-testing/`.

## How to Use

1. Find the error message substring in the section headings below
2. Read the root cause and correct pattern
3. Check the working example to confirm the fix matches existing conventions
4. Apply the fix

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

**Related:** `ivy-model-editing` skill > Relations section

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

**Related:** `ivy-model-editing` skill > Invariants section

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

**Related:** `ivy-model-editing` skill > Invariants, Actions sections

---

## 4. `assumption failed` (isolate assumption violation)

**Trigger:** An isolate's assumptions about another isolate's behavior are not satisfied.

**Root Cause:** The specification of the assumed isolate does not guarantee what the assuming isolate expects.

**Correct Pattern:**
1. Run `ivy_model_info` to list all isolates
2. Check each isolate's assumptions against its specification
3. Strengthen the assumed isolate's specification, or weaken the assumption

**Working Examples:** Search for `object` and `specification` blocks in the protocol family.

**Related:** `ivy-model-editing` skill > Isolates section

---

## 5. `type mismatch` / `type error`

**Trigger:** Incompatible types in an expression (e.g., using `nat` where `packet_type` is expected).

**Root Cause:** Ivy's type system is strict with no implicit coercions.

**Correct Pattern:** Ensure all variables and expressions have consistent types. Check type declarations.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:226` — `function initial_max_stream_data_uni_server_0rtt : stream_pos`

**Related:** `ivy-model-editing` skill > Type Declarations section

---

## 6. `circular dependency`

**Trigger:** Two or more modules or objects depend on each other via includes.

**Root Cause:** Ivy does not support circular include dependencies.

**Correct Pattern:** Structure files as a DAG. Introduce abstract interfaces to break cycles.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:3-5` — linear include chain: `include quic_types`, `include quic_transport_error_code`, `include quic_stream`
- `protocol-testing/bgp/bgp_utils/random_value.ivy:3` — single include: `include bgp_type`

**Related:** `ivy-model-editing` skill > Include Directives section

---

## 7. `not well-founded`

**Trigger:** A recursive definition does not terminate.

**Root Cause:** Ivy requires well-founded recursion for soundness.

**Correct Pattern:** Add a termination measure or restructure to avoid recursion.

**Related:** `ivy-model-editing` skill > Definitions section

---

## 8. `uninterpreted sort has no instances`

**Trigger:** A type was declared but never given concrete values.

**Root Cause:** The type is abstract with no constructors or axioms.

**Correct Pattern:** Add at least one constructor or axiom providing instances of the sort.

**Related:** `ivy-model-editing` skill > Type Declarations section

---

## 9. Z3 timeout / `unknown`

**Trigger:** Verification takes too long; the SMT solver cannot decide.

**Root Cause:** Proof obligation too complex (deep quantifier nesting, large isolates, complex arithmetic).

**Correct Pattern:**
1. Break into smaller lemmas
2. Add ghost state or auxiliary invariants to guide the prover
3. Use `isolate` boundaries to limit what the solver must reason about
4. Reduce quantifier nesting depth

**Related:** `ivy-verification` skill > Z3 timeout section

---

## 10. `multiple definitions`

**Trigger:** Same symbol declared in multiple included files.

**Root Cause:** Include graph brings in conflicting declarations.

**Correct Pattern:**
1. Run `ivy_include_graph` to trace the duplicate
2. Remove one declaration or namespace it inside an `object`

**Related:** `ivy-model-editing` skill > Module System section

---

## 11. `cannot find isolate X`

**Trigger:** Misspelled isolate name or missing declaration.

**Root Cause:** The isolate name in the command does not match any declaration in the file.

**Correct Pattern:**
1. Check spelling of the isolate name
2. Run `ivy_model_info` to list declared isolates

**Related:** `ivy-model-editing` skill > Isolates section

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

**Related:** `ivy-model-editing` skill > Common Pitfalls > Forgetting `after init` blocks

---

## Protocol-Specific Patterns

This section will grow as new protocol-specific errors are encountered. Add entries here when an error pattern is specific to a protocol family (BGP, QUIC, CoAP, etc.) rather than being a general Ivy language issue.
