---
name: propagation-patterns
description: "Use when propagating field or variant changes across Ivy spec layers. Provides type-change impact analysis patterns and Ivy-to-C++ encoding tables."
user-invocable: false
---

# Propagation Patterns

**Type:** flexible — adapt principles to context.

Use this skill when propagating an Ivy type change to serializer/deserializer state machines. It provides the exact C++ patterns, encoding conventions, and asymmetry warnings needed to generate correct edits.

## Authority Rule

The `ivy_propagation(mode="impact", ...)` tool output is the **single source of truth** for which files to edit; see `.claude/rules/propagation-authority.md` for the full rule set. This skill does not independently classify files.

## Ivy Type-to-C++ Encoding Table

| Ivy Type | Byte Count | Ser Method | Deser Method | State Name Convention |
|---|---|---|---|---|
| `byte` | 1 | `setn(res, 1)` | `getn(res, 1)` | `{prot}_s_{field_name}` |
| `stream_data` / `cid` | variable | byte-by-byte loop via `data_remaining` | byte-by-byte loop via `data_remaining` | `{prot}_s_{field_name}` |
| `microseconds` / timestamp | 8 | `setn(res, 8)` | `getn(res, 8)` + check for `reverse_bytes` | `{prot}_s_{field_name}` |
| `pkt_num` / integer | 1-4 | `setn(res, N)` | `getn(res, N)` | `{prot}_s_{field_name}` |
| `frame.arr` | variable | `open_tag`/`close_tag` dispatch | `open_tag`/`close_tag` dispatch | `{prot}_s_payload` |

## Add-Field Pattern

To add a new scalar field to a struct type:

1. **Type definition file:** Add `field_name : ivy_type` to the struct body at the specified position.

2. **Serializer:** Add enum state `{prot}_s_{field_name}` to the enum. Add a `case` in `set()` that calls `setn(res, byte_count)` and transitions to the next state. Update the **preceding** state's transition target to point to the new state.

3. **Deserializer:** Mirror the serializer changes but use `getn(res, byte_count)` instead of `setn`. Check the existing deserializer for byte-order handling conventions (e.g., `reverse_bytes` for multi-byte fields) and apply the same convention to the new field.

4. **Hardcoded counters:** Check the deserializer for hardcoded payload length values (e.g., `payload_length = 12`) and fixed iteration caps (e.g., `current_ping_size == 5`). Adding a field changes the wire length, so these constants may need updating. `ivyc` compilation will NOT catch incorrect hardcoded values. Always flag these for the user.

### MiniP Concrete Example

For the MiniP Add-Field worked example with enum, init-transition, new case, and deserializer mirror, see `references/minip-examples.md`.

## Add-Variant Pattern

To add a new frame variant to a variant type:

1. **Variant type definition file:** Add a new nested object inside the parent type's object block:
   ```ivy
   object {variant_name} = {
       variant this of {parent} = struct {
           field_name : field_type
       }
   }
   ```
   Note: Ivy uses `variant this of frame = struct { ... }` syntax, NOT `type this = struct { ... }` for variant members.

2. **Serializer `open_tag()`:** Add a new case for `tag == N` that sets `frame_type` to the wire type code and transitions to the variant's initial state. Add the variant's field states to the enum and `set()`.

3. **Deserializer `open_tag()`:** Add a new `if (frame_type == 0xNN)` branch that transitions to the variant's initial state and returns the tag index. Add the variant's field states to `get()`.

4. **Tag index rule:** Must be the next sequential integer after the last existing variant. The variant's declaration order in the Ivy source must match its tag integer in the C++ `open_tag()` dispatch.

5. **Iteration caps:** Check the deserializer for hardcoded iteration limits (e.g., `current_ping_size == 5`). Adding a new variant may require updating these caps.

### MiniP Variant Example

For the MiniP Add-Variant worked example with Ivy definition, tag dispatch in serializer and deserializer, and state transitions, see `references/minip-examples.md`.

## Ser/Deser Asymmetry Warnings

These asymmetries apply across all protocols. Always check for them:

- **Not mirrors.** Serializer and deserializer are NOT symmetric. Always read both files before editing either one.
- **Byte-order handling.** Check for `reverse_bytes()` in the existing deserializer. If multi-byte fields use it, apply the same convention to new fields.
- **State count differences.** State counts may differ between ser and deser (e.g., QUIC: 55 ser states vs 53 deser states). Do not assume they match.
- **Counter management.** The `data_remaining` counter management differs between ser and deser for variable-length fields.
- **Hardcoded constants (MiniP-specific).** The MiniP deserializer at `protocol-testing/minip/minip_stack/ping_deser.ivy` has `payload_length = 12` (hardcoded wire length) and `current_ping_size == 5` (iteration cap). These are semantic values that `ivyc` compilation cannot validate. Adding a field or variant may require updating them. Always flag hardcoded integer literals in the deser's `set()`/`get()`/`open_list_elem()` methods for user review.

## Integration

- **LOADED BY:** build workflow (Phase 3 Write when a type change affects serializers across layers), verify workflow (Phase 6 Diagnose when a failure traces to an asymmetry between ser and deser).
- **CALLS:** `ivy_propagation` (impact mode) as the authoritative impact source — for the invocation shape, load the ivy-toolkit skill via `Skill(skill="panther-ivy-plugin:ivy-toolkit")` and consult its tool-invocation-examples reference.

**Related skills:**
- **`specification-patterns`** — 14-layer template and where serializer files sit in it.
- **`ivy-writing-guide`** — load this skill via the `Skill` tool and consult its `references/serializer-patterns.md` for the C++ state-machine internals.
- **`ivy-toolkit`** — `ivy_propagation` tool parameters.
