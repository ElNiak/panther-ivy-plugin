---
name: ivy-model-editing
description: "Ivy language reference for writing and editing .ivy specification files — declarations, state, actions, invariants, modules, includes. Use when creating or modifying Ivy protocol models. Triggers on 'write ivy', 'add relation', 'add action', 'ivy syntax', 'new invariant', 'edit ivy', 'ivy declaration'."
context: fork
paths: "**/*.ivy"
---

# Ivy Model Editing Reference

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill is the language reference for writing and editing `.ivy` files. It covers syntax, declaration patterns, and best practices for formal protocol model authoring.

---

## File Header

Every Ivy file begins with a language version pragma:
```ivy
#lang ivy1.7
```
This must be the first line. Version 1.7 is the current standard used in PANTHER protocol models.

---

## Type Declarations

```ivy
type packet_id                              # Uninterpreted type
type message_type = {request, response, error}  # Enumerated type
type cid                                    # Abstract identifier
type stream_kind = {unidir, bidir}          # Protocol-specific enum
interpret bit -> bv[1]                      # Bitvector interpretation
```

Built-in types: `bool`, `nat` (natural numbers), `int` (integers), `bv[N]` (bitvectors).

**Related:** `ivy-error-patterns` entry #5 (type mismatch), entry #8 (no instances)

---

### Relations

> **Before writing a new relation**, grep `protocol-testing/` for similar declarations to see the canonical pattern for your protocol family: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Relations declare state predicates over typed arguments.

```ivy
relation sent(P: packet_id, N: node_id)
relation connected(N1: node_id, N2: node_id)
relation conn_seen(C:cid)
```

Relations are boolean-valued and represent protocol model state.

**Parameter naming**: Always use single uppercase letters (C, S, P, N, D) as parameter names. Multi-character lowercase names (e.g., `src`, `dst`) are resolved as symbol references, not fresh binders — this causes a `'src' not found` error. See `ivy-error-patterns` entry #1.

**Related:** `ivy-error-patterns` entry #1 (parameter name collision), entry #12 (missing after init)

---

### Functions and Individuals

> **Before writing a new function**, grep `protocol-testing/` for similar declarations: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

```ivy
function packet_dest(P: packet_id) : node_id
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num
individual my_id : node_id
individual the_cid : cid
```

---

### Actions

> **Before writing a new action**, grep `protocol-testing/` for similar patterns: `Grep(pattern="action.*=", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Actions model state transitions. They have preconditions (`require`), effects (assignments),
and postconditions (`ensure`):

```ivy
action send(src: node_id, dst: node_id, p: packet_id) = {
    require connected(src, dst);
    require ~sent(p, dst);
    sent(p, dst) := true;
    ensure sent(p, dst)
}
```

- `require`: precondition that must hold (see also: `assume` vs `require` trap below)
- `ensure`: postcondition that must hold after
- `:=`: deterministic assignment
- `assume`: introduces an assumption (use sparingly, weakens the model — prefer `require`)

**Parameter naming**: Same single uppercase letter convention applies to action parameters.

**Related:** `ivy-error-patterns` entry #3 (invariant failed), entry #12 (missing after init)

---

## Invariants

Properties that must hold in every reachable state:
```ivy
invariant sent(P, N) -> connected(source(P), N)
invariant ack_pending(P) -> sent(P, dest(P))
```

Invariants are checked inductively: must hold initially and be preserved by every action.

**Ungrounded variables**: `invariant sent(P, N)` means "for all P and N, sent(P,N) is true" — probably not intended. Always write conditional invariants. See `ivy-error-patterns` entry #2.

**Overly strong invariants**: An invariant that is too strong will fail on the initial state. Start weak, strengthen as needed.

**Related:** `ivy-error-patterns` entry #2 (ungrounded variable), entry #3 (invariant failed)

---

## Definitions

```ivy
definition f(X:t) = X + 1
```

Definitions must be well-founded (no recursive definitions that don't terminate). See `ivy-error-patterns` entry #7.

---

## Object System

```ivy
object frame = {
    type id
    relation valid(F: id)
    action create : id
    action destroy(f: id)
}
```

Naming conventions: `snake_case` for actions/relations/functions; `PascalCase` for module names.

---

## Module System

### Parameterized Modules

```ivy
module ordered_set(elem) = {
    type this
    relation contains(S: this, E: elem)
    action add(s: this, e: elem) returns (s2: this)
}
```

### Instances

```ivy
instance packet_set : ordered_set(packet_id)
instance node_set : ordered_set(node_id)
```

**Related:** `ivy-error-patterns` entry #10 (multiple definitions)

---

## Isolates

Isolates define verification boundaries separating specification from implementation:
```ivy
isolate protocol_spec = {
    object client = { ... }
    object server = { ... }
    specification { invariant ... }
}
```

Keep isolates focused on one component for easier solving. Large isolates hide bugs in complexity.

**Related:** `ivy-error-patterns` entry #4 (assumption failed), entry #11 (cannot find isolate)

---

## Include Directives

```ivy
include collections
include order
include my_protocol_types
```

Includes search the Ivy standard library and the current directory. No `.ivy` extension in the directive. Circular includes are not supported — structure the include graph as a DAG.

**Related:** `ivy-error-patterns` entry #6 (circular dependency)

---

## Initialization

All mutable relations and functions must be explicitly initialized in `after init` blocks:

```ivy
after init {
    conn_seen(C) := false;
    last_pkt_num(C, L) := 0;
    conn_closed(C) := false;
}
```

Without `after init`, relations start with arbitrary (unconstrained) values, which causes invariants to fail on the initial state. See `ivy-error-patterns` entry #12.

---

## RFC Traceability Tags

Every `require`, `ensure`, `assume`, or `assert` should include a bracket tag comment:

```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
ensure stream_data_delivered;               # [rfc9000:2.2]
```

Tag format: `rfc{N}:{section}` (e.g., `rfc9000:4.1`). One requirement per tag.

---

## Common Pitfalls and Best Practices

### Pitfalls

1. **Forgetting `after init` blocks**: Relations and functions start with arbitrary values unless explicitly initialized. See `ivy-error-patterns` entry #12.

2. **Ungrounded variables in invariants**: `invariant sent(P, N)` means "for all P and N, sent(P,N) is true" — probably not what you intended. See `ivy-error-patterns` entry #2.

3. **Overly strong invariants**: Too strong will fail on initial state. Start weak, strengthen as needed.

4. **Missing `require` clauses**: Without preconditions, actions can be called in any state.

5. **Circular includes**: Ivy does not support circular include dependencies. See `ivy-error-patterns` entry #6.

6. **Using `assume` instead of `require`**: `assume` weakens the model by introducing unverified assumptions.

7. **Multi-character lowercase parameter names**: `relation r(src:t)` — `src` is resolved as a symbol reference, not a fresh binder. Always use single uppercase letters. See `ivy-error-patterns` entry #1.

### Best Practices

1. **Name conventions**: `snake_case` for actions/relations/functions. `PascalCase` for module names.
2. **Single uppercase parameter names**: Use C, S, P, N, D as parameter names in relation/function/action declarations.
3. **Small isolates**: Keep isolates focused on one component for easier solving.
4. **Incremental verification**: Verify incrementally — small changes are easier to debug than large batches.
5. **Separate specification from implementation**: Use `specification` and `implementation` blocks.
6. **Use `after init`**: Explicitly initialize all mutable state.
7. **Minimize axioms**: Every axiom is an unverified assumption.

---

## Common Syntax Traps

These patterns produce misleading error messages. See `ivy-error-patterns` skill for the full catalog.

### Trap 1: Parameter Name Collision

```ivy
# WRONG — 'src' not found (Ivy resolves parameter names as symbol references)
relation update_processed(src:bgp_id, dst:bgp_id)

# RIGHT — single uppercase letter parameter names are unambiguous fresh binders
relation update_processed(S:bgp_id, D:bgp_id)
```

Ivy resolves the token before `:` in a parameter list as a symbol. Use single uppercase letters (C, S, P, N, D) as parameter names. See `ivy-error-patterns` entry #1.

### Trap 2: Missing `after init` with Misleading Invariant Failure

```ivy
# Invariant fails on initial state — but the invariant is correct!
relation conn_seen(C:cid)
invariant conn_seen(C) -> connected(C)
# Error: invariant failed (because conn_seen starts as arbitrary, not false)

# FIX — initialize the relation
after init {
    conn_seen(C) := false;
}
```

See `ivy-error-patterns` entry #12.

### Trap 3: `assume` vs `require` Confusion

```ivy
# WRONG — weakens the model; the assumption is never verified
action handle(p:packet) = {
    assume valid(p);
    # ...
}

# RIGHT — precondition that callers must satisfy, verified by ivy_check
action handle(p:packet) = {
    require valid(p);
    # ...
}
```

### Trap 4: Ungrounded Variable in Invariant

```ivy
# WRONG — "for all P and N, sent(P,N) is true" (probably not intended)
invariant sent(P, N)

# RIGHT — constrained relationship
invariant sent(P, N) -> connected(source(P), N)
```

See `ivy-error-patterns` entry #2.

### Trap 5: Overly Strong Invariant

```ivy
# WRONG — fails immediately because conn_seen starts false for some C
invariant connected(C)

# RIGHT — conditional invariant
invariant connected(C) -> conn_seen(C)
```

---

## Integration

**Related skills:**
- **ivy-error-patterns** — full catalog of Ivy error messages mapped to root causes and fixes
- **ivy-debugging-methodology** — mandatory pre-fix checklist for debugging verification failures
- **specification-patterns** — where to place each declaration type (14-layer template)
- **ivy-writing-guide** — test specification patterns and RFC annotation
- **ivy-toolkit** — MCP tool documentation

**Related agents:**
- **model-reviewer** — reviews model quality, flags syntax traps and anti-patterns
- **spec-analyst** — verification and diagnosis

**IMPORTANT**: Always use ivy-tools MCP tools for verification and compilation — never invoke `ivy_check`, `ivyc`, `ivy_show`, or `ivy_to_cpp` via Bash. See `ivy-toolkit` skill for tool selection and invocation patterns.
