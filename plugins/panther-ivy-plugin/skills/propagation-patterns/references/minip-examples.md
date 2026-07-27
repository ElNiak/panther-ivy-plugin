# MiniP Worked Examples

Concrete, file-level examples of the Add-Field and Add-Variant patterns applied to the MiniP protocol. Load this file when propagating a type change in MiniP, or when reviewing a pull request that edits MiniP ser/deser state machines.

## Add-Field: inserting `seq_num : byte` before the payload

<worked_example>

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

</worked_example>

## Add-Variant: adding an `error` frame variant

<worked_example>

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

</worked_example>

## Hardcoded constants (MiniP-specific)

The MiniP deserializer at `protocol-testing/minip/minip_stack/ping_deser.ivy` has `payload_length = 12` (hardcoded wire length) and `current_ping_size == 5` (iteration cap). These are semantic values that `ivyc` compilation cannot validate. Adding a field or variant may require updating them. Always flag hardcoded integer literals in the deser's `set()`/`get()`/`open_list_elem()` methods for user review.
