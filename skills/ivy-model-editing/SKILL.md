---
name: ivy-model-editing
description: Use when editing Ivy formal specification files (.ivy). Covers Ivy syntax, declaration types (type, relation, action, object, module, instance, isolate), module system, and best practices for protocol modeling.
---

# Ivy Model Editing Guide

## Language Basics

### File Header

Every Ivy file begins with a language version pragma as a comment:

```ivy
#lang ivy1.7
```

This must be the first line. It selects the Ivy language version and determines available features.
Version 1.7 is the current standard version used in PANTHER protocol models.

### Type Declarations

Types define the sorts (domains) of values in the model.

```ivy
type packet_id
type node_id
type message_type = {request, response, error}
```

- **Uninterpreted types**: `type packet_id` -- abstract, no built-in structure.
- **Enumerated types**: `type msg = {a, b, c}` -- finite set of named values.
- **Subtypes**: Declared via interpretation or refinement.
- **Built-in types**: `bool`, `nat` (natural numbers), `int` (integers), `bv[N]` (bitvectors).

### Relations

Relations declare state predicates over typed arguments.

```ivy
relation sent(P: packet_id, N: node_id)
relation connected(N1: node_id, N2: node_id)
relation ack_pending(P: packet_id)
```

Relations are boolean-valued. They represent the state of the protocol model.

### Functions and Individuals

```ivy
# A function from one sort to another
function packet_dest(P: packet_id) : node_id

# A constant (0-ary function)
individual my_id : node_id
```

### Actions

Actions model state transitions. They have preconditions (`require`), effects (assignments),
and postconditions (`ensure`).

```ivy
action send(src: node_id, dst: node_id, p: packet_id) = {
    require connected(src, dst);
    require ~sent(p, dst);
    sent(p, dst) := true;
    ensure sent(p, dst)
}
```

- `require`: precondition that must hold when the action is called.
- `ensure`: postcondition that must hold after the action completes.
- `:=`: deterministic assignment.
- `assume`: introduces an assumption (use sparingly, weakens the model).

### Invariants

Invariants express properties that must hold in every reachable state.

```ivy
invariant sent(P, N) -> connected(source(P), N)
invariant ack_pending(P) -> sent(P, dest(P))
```

Invariants are checked inductively: they must hold initially and be preserved by every action.

### Axioms and Conjectures

```ivy
# Axiom: assumed to be true (not checked)
axiom connected(X, Y) -> connected(Y, X)

# Conjecture: checked but not used inductively
conjecture forall P. sent(P, dest(P)) -> ack_pending(P)
```

## Object System

### Basic Objects

Objects group related declarations. They introduce a namespace.

```ivy
object frame = {
    type id
    relation valid(F: id)

    action create : id
    action destroy(f: id)

    implementation {
        action create returns (f: id) = {
            valid(f) := true
        }
        action destroy(f: id) = {
            require valid(f);
            valid(f) := false
        }
    }
}
```

### Type `this`

Inside an object, `type this` declares the object itself as a parameterized type:

```ivy
object counter = {
    type this

    individual val(X: this) : nat

    action increment(c: this) = {
        val(c) := val(c) + 1
    }
}
```

### Nested Objects

Objects can be nested to create hierarchies:

```ivy
object protocol = {
    object client = {
        action connect(srv: server.endpoint)
    }
    object server = {
        type endpoint
        action accept(c: client)
    }
}
```

### Definitions

Definitions introduce named abbreviations:

```ivy
definition is_idle(N: node_id) = ~exists P. ack_pending(P) & packet_dest(P) = N
```

## Module System

### Parameterized Modules

Modules are templates that can be instantiated with different types:

```ivy
module ordered_set(elem) = {
    type this

    relation contains(S: this, E: elem)
    relation le(S1: this, S2: this)

    action add(s: this, e: elem) returns (s2: this)

    # ... implementation ...
}
```

### Instances

Instantiate modules with concrete types:

```ivy
instance packet_set : ordered_set(packet_id)
instance node_set : ordered_set(node_id)
```

After instantiation, use as `packet_set.contains(s, p)`, `packet_set.add(s, p)`, etc.

### Isolates

Isolates define verification boundaries. They separate specification from implementation:

```ivy
isolate protocol_spec = {
    # What is verified here
    object client = { ... }
    object server = { ... }

    # What is assumed (not verified, taken as axioms)
    specification {
        invariant ...
    }
}
```

Isolates control what the SMT solver must reason about, making verification tractable.

## Protocol Modeling Patterns

### Client/Server Roles

```ivy
#lang ivy1.7

type node_id
type msg_id
type msg_type = {syn, syn_ack, ack, data, fin}

object client = {
    individual id : node_id
    relation connected
    relation waiting_ack(M: msg_id)

    after init {
        connected := false;
        waiting_ack(M) := false
    }

    action send_syn(srv: node_id) = {
        require ~connected;
        # ... send SYN packet
    }
}

object server = {
    individual id : node_id
    relation listening
    relation has_client(C: node_id)

    after init {
        listening := true;
        has_client(C) := false
    }

    action handle_syn(c: node_id) = {
        require listening;
        # ... send SYN-ACK
    }
}
```

### State Machines

Model protocol states explicitly:

```ivy
type conn_state = {idle, connecting, established, closing, closed}

individual state : conn_state

after init {
    state := idle
}

action open_connection = {
    require state = idle;
    state := connecting
}

action connection_established = {
    require state = connecting;
    state := established
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

## Include Directives and Library Organization

### Include Syntax

```ivy
include collections
include order
include my_protocol_types
```

Includes search the Ivy standard library and the current directory. The included file must
be a valid `.ivy` file (without the extension in the include directive).

### Recommended File Organization

```
protocol_model/
  types.ivy          # Shared type declarations
  network.ivy        # Network model (links, delivery)
  client.ivy         # Client-side protocol logic
  server.ivy         # Server-side protocol logic
  invariants.ivy     # Cross-cutting invariants
  main.ivy           # Top-level file that includes all others
```

## Common Pitfalls and Best Practices

### Pitfalls

1. **Forgetting `after init` blocks**: Relations and functions start with arbitrary values
   unless explicitly initialized. Always set initial state.

2. **Ungrounded variables in invariants**: Every variable in an invariant must be universally
   quantified (implicitly) or bound. `invariant sent(P, N)` means "for all P and N, sent(P,N)
   is true" -- probably not what you intended.

3. **Overly strong invariants**: An invariant that is too strong will fail on the initial state
   or be impossible to maintain. Start with weak invariants and strengthen as needed.

4. **Missing `require` clauses**: Without preconditions, actions can be called in any state,
   making invariant preservation harder to verify.

5. **Circular includes**: Ivy does not support circular include dependencies. Structure files
   as a DAG.

6. **Using `assume` instead of `require`**: `assume` weakens the model by introducing
   unverified assumptions. Prefer `require` for preconditions.

### Best Practices

1. **Name conventions**: Use `snake_case` for actions, relations, and functions.
   Use `PascalCase` for module names. Use descriptive type names.

2. **Small isolates**: Keep isolates focused on one component. Smaller proof obligations
   are easier for the SMT solver.

3. **Incremental verification**: Check frequently as you build the model. Do not write
   hundreds of lines before running `ivy_check`.

4. **Document invariants**: Add comments explaining why each invariant is needed and what
   property it captures.

5. **Separate specification from implementation**: Use `specification` and `implementation`
   blocks within isolates to cleanly separate concerns.

6. **Use `after init`**: Explicitly initialize all mutable state to avoid reasoning about
   arbitrary initial values.

7. **Minimize axioms**: Every axiom is an unverified assumption. Prefer provable invariants.

**IMPORTANT**: Always use ivy-tools MCP tools for Ivy verification operations. Never run ivy_check, ivyc, ivy_show, or ivy_to_cpp directly via Bash. Use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`, `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile`, and `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` instead.
