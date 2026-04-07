# Phase 2: Blueprint Generation

## Purpose

Produce a concrete file architecture adapted to the protocol profile from Phase 1.

## Ivy Concepts

- **`include` composition**: Textual insertion, not module import. The included file is pasted in place.
- **`#lang ivy1.7`**: Required on every `.ivy` file as the first line.
- **Include DAG**: Flows one direction — test files include everything transitively. No circular includes.

## File Naming Convention

- **Stack/protocol files**: `{proto}_*.ivy` (e.g., `quic_packet.ivy`, `quic_frame.ivy`). Model the protocol itself.
- **Infrastructure/entity files**: `ivy_{proto}_*.ivy` (e.g., `ivy_quic_server.ivy`, `ivy_quic_shim_client.ivy`). Ivy testing infrastructure wrapping the protocol model.

## Blueprint Directory Tree

Generate this tree, adapted to the protocol profile. Remove conditional directories that do not apply.

```
protocol-testing/{proto}/
+-- {proto}_stack/                        # Core protocol model
|   +-- {proto}_types.ivy                 # Base types, enums, bit-vector interpretations
|   +-- {proto}_message.ivy               # Message structs + message_event actions
|   +-- {proto}_state.ivy                 # State tracking (relations, functions, after init)
|   +-- {proto}_connection.ivy            # Aggregator: includes all stack files in order
+-- {proto}_utils/                        # Serialization, helpers, locale
|   +-- {proto}_ser.ivy                   # Struct-to-bytes serialization
|   +-- {proto}_deser.ivy                 # Bytes-to-struct deserialization
|   +-- {proto}_locale.ivy                # Network locale setup
+-- {proto}_entities/                     # Entity instantiation (one file per role)
|   +-- ivy_{proto}_{role_a}.ivy          # Role A entity: parameters + endpoint instantiation
|   +-- ivy_{proto}_{role_b}.ivy          # Role B entity: parameters + endpoint instantiation
+-- {proto}_entities_behavior/            # Endpoint modules + role-specific constraints
|   +-- {proto}_endpoint.ivy              # Parameterized endpoint modules (behavior action)
|   +-- ivy_{proto}_{role_a}_behavior.ivy # Role A behavioral constraints
|   +-- ivy_{proto}_{role_b}_behavior.ivy # Role B behavioral constraints
+-- {proto}_shims/                        # Wire format bridges
|   +-- {proto}_shim.ivy                  # Base shim (central composition point)
|   +-- ivy_{proto}_shim_{role_a}.ivy     # Role A send/receive
|   +-- ivy_{proto}_shim_{role_b}.ivy     # Role B send/receive
+-- {proto}_config/                       # Parameter configurations
|   +-- ivy_{proto}_standard_config.ivy
+-- {proto}_tests/                        # Test specifications
|   +-- {role_b}_tests/                   # Tests targeting role B (Ivy acts as role A)
|   |   +-- {proto}_{role_b}_test.ivy
|   +-- {role_a}_tests/                   # Tests targeting role A (Ivy acts as role B)
|       +-- {proto}_{role_a}_test.ivy
+-- {proto}_attacks_stack/                # (conditional: attack testing)
|   +-- forged_{proto}_message.ivy
|   +-- attack_connection.ivy             # Aggregator for attack types
+-- {proto}_extensions/                   # (conditional: extensible protocol)
|   +-- {proto}_{extension_name}.ivy
+-- {proto}_fsm/                          # (conditional: complex state machine)
|   +-- {proto}_fsm_sending.ivy
|   +-- {proto}_fsm_receiving.ivy
+-- tls_stack/                            # (conditional: own crypto layer)
    +-- tls_protocol.ivy
```

### Simplification Rules

- **Stateless**: no `_state.ivy`, no `_connection.ivy` aggregator (types + message suffice)
- **No attacks**: omit `_attacks_stack/`
- **P2P**: single entity file, single shim
- **No FSM**: omit `_fsm/` directory
- **No crypto**: omit `tls_stack/` and protection files
- **Not extensible**: omit `_extensions/`

## Module Dependency Graph

Produce a DAG showing include relationships. The general pattern flows from test files down through shims to the stack:

```
{proto}_{role}_test.ivy
  +-- ivy_{proto}_shim_{opposite_role}
  |     +-- {proto}_shim.ivy
  |           +-- {proto}_connection.ivy (aggregator)
  |           |     +-- {proto}_types.ivy
  |           |     +-- {proto}_message.ivy
  |           |     +-- {proto}_state.ivy
  |           +-- ivy_{proto}_{role_a}.ivy (entity)
  |           +-- ivy_{proto}_{role_b}.ivy (entity)
  |           +-- {proto}_ser.ivy / {proto}_deser.ivy
  +-- ivy_{proto}_{opposite_role}_behavior
  +-- ivy_{proto}_standard_config
```

## Type Mapping Table

Map RFC concepts to Ivy constructs. Syntax details are explained in Phase 3; this is a preview:

```
RFC Concept                  -> Ivy Construct                    -> File
[protocol-specific ID]       -> type {name}                      -> {proto}_types.ivy
[message type enum]          -> type {name} = {v1, v2, ...}      -> {proto}_types.ivy
[message format]             -> struct { field : type, ... }      -> {proto}_message.ivy
[protocol event]             -> action {name}_event(src,dst,msg)  -> {proto}_message.ivy
[session state]              -> relation {name}(S:session_id)     -> {proto}_state.ivy
[negotiated parameters]      -> variant types in config file      -> {proto}_config/
```

---

**STOP.** Present the file tree, dependency graph, and type mapping table to the user. Do NOT write any `.ivy` files until the user approves the architecture.
