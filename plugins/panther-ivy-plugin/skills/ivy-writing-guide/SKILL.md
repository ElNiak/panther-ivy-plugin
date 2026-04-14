---
name: ivy-writing-guide
description: "Ivy syntax reference: declarations, module system, RFC annotations, test spec patterns. Use when writing or editing .ivy files."
user-invocable: false
context: fork
paths: "**/*.ivy"
---

# Ivy Writing Guide

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill combines the Ivy language reference, test specification patterns, and RFC bracket-tag annotation conventions. Use it whenever editing or creating `.ivy` files.

## Ivy Language Basics

### File Header

Every Ivy file begins with a language version pragma:
```ivy
#lang ivy1.7
```
This must be the first line. Version 1.7 is the current standard used in PANTHER protocol models.

### Type Declarations

```ivy
type packet_id                              # Uninterpreted type
type message_type = {request, response, error}  # Enumerated type
type cid                                    # Abstract identifier
type stream_kind = {unidir, bidir}          # Protocol-specific enum
interpret bit -> bv[1]                      # Bitvector interpretation
```

Built-in types: `bool`, `nat` (natural numbers), `int` (integers), `bv[N]` (bitvectors).

### Relations (State Predicates)

> **Before writing a new relation**, grep for similar declarations: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

```ivy
relation sent(P: packet_id, N: node_id)
relation connected(N1: node_id, N2: node_id)
relation conn_seen(C:cid)
```

Relations are boolean-valued and represent protocol model state.

### Functions and Individuals

> **Before writing a new function**, grep for similar declarations: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

```ivy
function packet_dest(P: packet_id) : node_id
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num
individual my_id : node_id
individual the_cid : cid
```

### Actions

> **Before writing a new action**, grep for similar patterns: `Grep(pattern="action.*=", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Actions model state transitions with preconditions, effects, and postconditions:
```ivy
action send(src: node_id, dst: node_id, p: packet_id) = {
    require connected(src, dst);
    require ~sent(p, dst);
    sent(p, dst) := true;
    ensure sent(p, dst)
}
```

- `require`: precondition that must hold
- `ensure`: postcondition that must hold after
- `:=`: deterministic assignment
- `assume`: introduces an assumption (use sparingly, weakens the model)

### Invariants

Properties that must hold in every reachable state:
```ivy
invariant sent(P, N) -> connected(source(P), N)
invariant ack_pending(P) -> sent(P, dest(P))
```

Invariants are checked inductively: must hold initially and be preserved by every action.

## Object System

```ivy
object frame = {
    type id
    relation valid(F: id)
    action create : id
    action destroy(f: id)
}
```

See the [README.md](README.md) for extended examples: `type this`, nested objects, axioms/conjectures.

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

### Isolates

Isolates define verification boundaries separating specification from implementation:
```ivy
isolate protocol_spec = {
    object client = { ... }
    object server = { ... }
    specification { invariant ... }
}
```

## Include Directives

```ivy
include collections
include order
include my_protocol_types
```

Includes search the Ivy standard library and the current directory. No `.ivy` extension in the directive.

## Test Specification Patterns

See [references/syntax-examples.md](references/syntax-examples.md) for test spec structure, role isolation, weight attributes, and variant patterns.

### Test File Checklist

1. `#lang ivy1.7` header
2. Protocol stack includes
3. Shim include for the role Ivy plays
4. Entity behavior include
5. `after init` block with socket/TLS setup
6. `export` declarations
7. `_finalize` with end-state checks

## RFC Bracket-Tag Annotations

Tag every `require`, `ensure`, `assume`, or `assert` with bracket tags: `# [rfc9000:4.1]`

See [references/syntax-examples.md](references/syntax-examples.md) for annotation workflow, tag conventions, and requirement manifests.

## Common Pitfalls and Best Practices

### Pitfalls

1. **Forgetting `after init` blocks**: Relations and functions start with arbitrary values unless explicitly initialized.

2. **Ungrounded variables in invariants**: `invariant sent(P, N)` means "for all P and N, sent(P,N) is true" -- probably not what you intended.

3. **Overly strong invariants**: Too strong will fail on initial state. Start weak, strengthen as needed.

4. **Missing `require` clauses**: Without preconditions, actions can be called in any state.

5. **Circular includes**: Ivy does not support circular include dependencies.

6. **Using `assume` instead of `require`**: `assume` weakens the model by introducing unverified assumptions.

7. **Missing _finalize**: Without _finalize, end-state properties are never checked.

8. **Correct role convention**: Server test = Ivy plays client. File name reflects what is tested.

### Best Practices

1. **Name conventions**: `snake_case` for actions/relations/functions. `PascalCase` for module names.
2. **Small isolates**: Keep isolates focused on one component for easier solving.
3. **Incremental verification**: Verify incrementally — small changes are easier to debug than large batches.
4. **Document invariants**: Add comments explaining why each invariant is needed.
5. **Separate specification from implementation**: Use `specification` and `implementation` blocks.
6. **Use `after init`**: Explicitly initialize all mutable state.
7. **Minimize axioms**: Every axiom is an unverified assumption.

## Protocol Modeling Patterns

### Client/Server Roles

```ivy
object client = {
    individual id : node_id
    relation connected
    after init { connected := false }
    action send_syn(srv: node_id) = {
        require ~connected;
    }
}

object server = {
    individual id : node_id
    relation listening
    after init { listening := true }
    action handle_syn(c: node_id) = {
        require listening;
    }
}
```

### State Machines

Model protocol states explicitly:
```ivy
type conn_state = {idle, connecting, established, closing, closed}
individual state : conn_state
after init { state := idle }

action open_connection = {
    require state = idle;
    state := connecting
}

invariant state = established -> server.has_client(client.id)
```

### Packet Types

```ivy
type packet_type = {handshake, data_pkt, control, close}
object packet = {
    type this
    function ptype(P: this) : packet_type
    function src(P: this) : node_id
    function dst(P: this) : node_id
    function seq(P: this) : nat
}
```

## Common Syntax Traps

See the `ivy-error-patterns` skill for the full error-to-fix lookup table with code examples. Key traps:

- **Parameter name collision** — use single uppercase letter params (`S:type`), not descriptive names that collide with existing symbols
- **Missing `after init`** — relations start arbitrary; invariants fail on initial state
- **`assume` vs `require`** — `assume` weakens the model unsoundly; use `require` for preconditions
- **Ungrounded variables** — `invariant sent(P,N)` means "for all P,N"; bind variables explicitly
- **Overly strong invariants** — `invariant connected(C)` fails immediately; use conditional form

For detailed code examples of each trap, see `references/syntax-examples.md`.

## Integration

- **LOADED BY:** build workflow (write phase)

**Related skills:**
- **specification-patterns** -- Where to place each declaration type (14-layer template)
- **methodology-reference** -- Verification after editing, RFC-to-Ivy mapping
- **ivy-toolkit** -- MCP tool documentation

**Related agents:**
- **model-reviewer** -- Reviews model quality
- **spec-analyst** -- Verification and diagnosis
