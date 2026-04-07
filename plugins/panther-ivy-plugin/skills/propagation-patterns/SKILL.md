---
name: propagation-patterns
description: "Pattern knowledge for propagating Ivy type changes to ser/deser state machines. Covers struct field addition and frame variant addition with encoding tables, concrete examples, asymmetry warnings, and hardcoded constant detection."
---

# Propagation Patterns

Use this skill when propagating an Ivy type change to serializer/deserializer state machines. It provides the exact C++ patterns, encoding conventions, and asymmetry warnings needed to generate correct edits.

## Authority Rule

The `ivy_change_impact` tool output is the **single source of truth** for which files to edit. This skill does not independently classify files. Follow these rules:
- Only edit files listed in `auto_propagate`. Never edit `manual_review` or `unaffected` files.
- For each `manual_review` file, present its `reason` string to the user.
- For hardcoded constants found during editing, always warn the user even if the file is in `auto_propagate`.

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

In `ping_ser.ivy`, the `ping_s_init` case transitions directly to `ping_s_payload` (`state = ping_s_payload`). The `ping_s_payload` state has no `set()` case — it is a sentinel for `open_tag()`/`close_tag()`.

To add `seq_num : byte` between packet header and payload:

**Enum change:**
```cpp
// Before:
enum {ping_s_init, ping_s_frame, ping_s_time, ping_s_payload} state;
// After:
enum {ping_s_init, ping_s_seq_num, ping_s_frame, ping_s_time, ping_s_payload} state;
```

**Init transition change:**
```cpp
// Before (in ping_s_init case):
state = ping_s_payload;
// After:
state = ping_s_seq_num;
```

**New case:**
```cpp
case ping_s_seq_num:
{
    setn(res, 1);
    state = ping_s_payload;
}
break;
```

**Deserializer:** Mirror the above changes using `getn(res, 1)`. Also check and update `payload_length` if hardcoded (MiniP has `payload_length = 12`).

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

To add an `error` frame variant to `frame` (in `ping_frame.ivy`) with `error_code : byte`:

**Ivy definition (add after the `timestamp` object):**
```ivy
    # (0x04)
    object error = {
        variant this of frame = struct {
            error_code : byte
        }
    }
```

**Serializer `open_tag()` (add after tag 2 block):**
```cpp
else if (tag == 3) {
    state = ping_s_error;
    frame_type = 0x04;
}
```

**Serializer enum + set():**
```cpp
// Add to enum:
ping_s_error
// Add case:
case ping_s_error:
{
    setn(res, 1);
}
break;
```

**Deserializer `open_tag()` (add after frame_type 0x03 block):**
```cpp
if (frame_type == 0x04) {
    state = ping_s_error;
    return 3;
}
```

## Ser/Deser Asymmetry Warnings

These asymmetries apply across all protocols. Always check for them:

- **Not mirrors.** Serializer and deserializer are NOT symmetric. Always read both files before editing either one.
- **Byte-order handling.** Check for `reverse_bytes()` in the existing deserializer. If multi-byte fields use it, apply the same convention to new fields.
- **State count differences.** State counts may differ between ser and deser (e.g., QUIC: 55 ser states vs 53 deser states). Do not assume they match.
- **Counter management.** The `data_remaining` counter management differs between ser and deser for variable-length fields.
- **Hardcoded constants (MiniP-specific).** The MiniP deserializer has `payload_length = 12` (hardcoded wire length) and `current_ping_size == 5` (iteration cap). These are semantic values that `ivyc` compilation cannot validate. Adding a field or variant may require updating them. Always flag hardcoded integer literals in the deser's `set()`/`get()`/`open_list_elem()` methods for user review.
