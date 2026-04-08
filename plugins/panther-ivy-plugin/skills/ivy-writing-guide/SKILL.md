---
name: ivy-writing-guide
description: "Internal knowledge skill — Ivy syntax, declarations, module system, RFC annotation. Do not invoke directly; loaded by build (Phase 3) and verify (test design)."
context: fork
paths: "**/*.ivy"
---

# Ivy Writing Guide

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill combines the Ivy language reference, test specification patterns, and RFC bracket-tag annotation conventions. Use it whenever editing or creating `.ivy` files.

---

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

```ivy
relation sent(P: packet_id, N: node_id)
relation connected(N1: node_id, N2: node_id)
relation conn_seen(C:cid)
```

Relations are boolean-valued and represent protocol model state.

### Functions and Individuals

```ivy
function packet_dest(P: packet_id) : node_id
function last_pkt_num(C:cid, L:quic_packet_type) : pkt_num
individual my_id : node_id
individual the_cid : cid
```

### Actions

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

---

## Test Specification Patterns

### Test Specification Structure

Every test specification follows this pattern:
```ivy
#lang ivy1.7

# 1. Includes
include order
include {prot}_infer
include file
include ivy_{prot}_shim_{role}
include ivy_{prot}_{role}_behavior

# 2. Initialization
after init {
    sock := net.open(endpoint_id.{role}, {role}.ep);
    {role}.set_tls_id(0);
    var extns := tls_extensions.empty;
    extns := extns.append(make_transport_parameters);
    call tls_api.upper.create(0, false, extns);
}

# 3. Exported actions (test mirror generates these)
export frame.ack.handle
export frame.stream.handle
export frame.crypto.handle
export packet_event

# 4. End-state verification
export action _finalize = {
    require is_no_error;
    require conn_total_data(the_cid) > 0;
}
```

### Key Components

#### Includes
Order matters. Critical includes:
- **Shim** (`ivy_{prot}_shim_{role}`) -- bridges formal model to implementation
- **Entity behavior** (`ivy_{prot}_{role}_behavior`) -- encodes RFC requirements

#### Initialization (`after init`)
Opens network sockets, sets TLS identifiers, creates transport parameter extensions, initializes TLS/security layer.

#### Exported Actions
`export` declarations tell the test mirror which actions to generate randomly. Z3/SMT ensures generated actions satisfy all `before` clause constraints.

#### _finalize() (End-State Verification)
Called when the test completes. Performs heuristic end-state checks:
```ivy
export action _finalize = {
    require is_no_error;
    require conn_total_data(the_cid) > 0;
}
```

### Role Isolation

- **Server tests** (`{prot}_server_test_*.ivy`): Ivy plays **client**, tests server IUT
- **Client tests** (`{prot}_client_test_*.ivy`): Ivy plays **server**, tests client IUT
- **MIM tests** (`{prot}_mim_test_*.ivy`): Ivy plays **man-in-the-middle**

### Test Variants

Base test files define common structure. Variant files extend them:
```ivy
#lang ivy1.7
include {prot}_server_test

# Weight attributes to bias generation
attribute frame.crypto.handle.weight = "5"
attribute frame.path_response.handle.weight = "5"

# Additional exports
export frame.new_connection_id.handle

# Variant-specific _finalize checks
after _finalize {
    require migration_completed;
}
```

### Weight Attributes

Higher weights make an action more likely to be chosen:
```ivy
attribute frame.stream.handle.weight = "10"   # Strongly prefer streams
attribute frame.rst_stream.handle.weight = "0.02"  # Rarely generate resets
```

### Common Variant Patterns (from QUIC)
- `*_stream.ivy` -- Basic stream data transfer
- `*_connection_close.ivy` -- Connection termination
- `*_retry.ivy` -- Retry mechanism testing
- `*_migration.ivy` -- Connection migration
- `*_0rtt.ivy` -- Zero-RTT early data
- `*_timeout.ivy` -- Timeout handling

### Test File Checklist

1. `#lang ivy1.7` header
2. Protocol stack includes (order, infer, file)
3. Shim include for the role Ivy plays
4. Entity behavior include
5. Transport parameters include (optional)
6. `after init` block with socket/TLS setup
7. `export` declarations for mirror-generated actions
8. `_finalize` with end-state checks
9. Weight attributes for test focus (optional)

---

## RFC Bracket-Tag Annotations

### Bracket Tag Syntax

Every `require`, `ensure`, `assume`, or `assert` statement should include a bracket tag comment:

```ivy
require conn_state = open;                  # [rfc9000:4.1]
require pkt.size <= max_packet_size;        # [rfc9000:14.1, rfc9000:8.1]
ensure stream_data_delivered;               # [rfc9000:2.2]
```

### Tag ID Convention

| Component | Format | Example |
|---|---|---|
| RFC number | `rfc` + number (no space) | `rfc9000` |
| Section | colon + section number | `:4.1` |
| Sub-section | dot-separated | `:4.1.2` |
| Full tag | `rfc{N}:{S}` | `rfc9000:4.1` |

### Annotation Workflow

1. **Identify requirements**: Consult RFC text and `*_requirements.yaml` manifest
2. **Write assertions with tags**: Tag each require/ensure/assert
3. **Check coverage**: Use `ivy_coverage` (mode="stats") MCP tool
4. **Review diagnostics**: Use `ivy_diagnostics` MCP tool

### Requirement Manifest

Create `{rfc}_requirements.yaml` files for full traceability:

```yaml
rfc: "RFC9000"
requirements:
  rfc9000:4.1:
    text: "A sender MUST NOT send data on a stream beyond the current limit"
    section: "4.1"
    level: MUST
    layer: stream
    testable: true
```

### Best Practices

1. **Tag every assertion** -- even trivial ones, for complete traceability
2. **One requirement per tag** -- don't combine unrelated requirements
3. **Use multi-tags sparingly** -- only when an assertion genuinely covers multiple requirements
4. **Keep manifests updated** -- add new requirements as you discover them
5. **Review orphaned tags** -- they indicate manifest-spec drift
6. **Level matters** -- MUST requirements should be covered first

---

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

## Integration

- **LOADED BY:** ivy-workflow-orchestrator Phase 3 (Write)

**Related skills:**
- **specification-patterns** -- Where to place each declaration type (14-layer template)
- **workflow-reference** -- Verification after editing, RFC-to-Ivy mapping
- **ivy-toolkit** -- MCP tool documentation

**Related agents:**
- **model-reviewer** -- Reviews model quality
- **spec-analyst** -- Verification and diagnosis
