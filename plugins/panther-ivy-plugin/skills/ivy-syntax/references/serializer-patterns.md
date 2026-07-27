# Ivy C++ Serializer/Deserializer Patterns

## ivy_binary_ser_128 Base Class

Custom serializers inherit from `ivy_binary_ser_128`. The base class default methods write 16-byte `int128_t` values for most callbacks. Custom serializers MUST override these to write protocol-correct byte widths.

### Base Class Defaults

| Method | Default Behavior | Override? |
|--------|-----------------|-----------|
| `set(int128_t inp)` | Writes 16 bytes via `setn(inp, sizeof(int128_t))` | **MUST** — write field-appropriate byte count |
| `set(bool inp)` | Casts to int128_t, writes 16 bytes | **MUST** if model has booleans |
| `open_list(int len)` | Writes 16 bytes of array length via `set((int128_t)len)` | **MUST** — override as no-op for protocols |
| `open_tag(int tag, const string&)` | Writes 16 bytes of tag via `set((int128_t)tag)` | **MUST** — write protocol variant header |
| `setn(int128_t inp, int len)` | Writes `len` bytes from `inp` (big-endian) | No — use as-is |
| `open_list_elem()` | No-op | Override for state transitions |
| `close_list()` | No-op | Override for state transitions |
| `close_tag()` | No-op | Override for state transitions |
| `open_struct()`, `close_struct()` | No-op | Rarely needed |
| `open_field(const string&)`, `close_field()` | No-op | Rarely needed |

### setn() Semantics

In the serializer, `setn(val, n)` writes `n` bytes FROM `val` to the output buffer (big-endian byte order). The `val` parameter is NOT modified. In the deserializer base class (`ivy_binary_deser_128`), `getn(val, n)` reads `n` bytes FROM the input buffer INTO `val`.

## Serialization Callback Sequence

Ivy's generated C++ calls these methods in a specific order for each type:

### Struct Serialization
```
open_struct()
  open_field("field1") → set(value)        → close_field()    // scalar
  open_field("field2") → open_list(len) ... → close_field()    // array
  open_field("field3") → open_tag(idx,name) ... → close_field() // variant in array
close_struct()
```

### Array Serialization
```
open_list(len)
  open_list_elem() → serialize element → close_list_elem()   // repeated per element
close_list()
```

### Variant Serialization (DIFFERENT signatures for ser vs deser)

**Serialization path** — Ivy calls with the variant index:
```cpp
// Generated code:
res.open_tag(0, "variant_name.case_a");  // (int tag, const string& name)
__ser(res, payload);
res.close_tag();
```

**Deserialization path** — custom serializer returns the chosen index:
```cpp
// Custom open_tag override:
virtual int open_tag(const std::vector<std::string> &tags) {
    // Read bytes from buffer to determine which variant
    return chosen_index;
}
```

These are DIFFERENT C++ overloads. Overriding `open_tag(vector<string>)` does NOT override `open_tag(int, string)`. Both must be implemented separately.

## State Machine Design

Protocol serializers use an enum-based state machine. Each state corresponds to a field or section of the wire format.

### Pattern
```cpp
class my_serializer : public ivy_binary_ser_128 {
    enum state_t { s_field1, s_field2, s_array_elem, s_done } state;

    virtual void set(int128_t res) {  // by-value, matches base
        switch (state) {
        case s_field1:
            setn(res, 2);  // write 2 bytes
            state = s_field2;
            break;
        case s_field2:
            setn(res, 4);  // write 4 bytes
            state = s_array_elem;
            break;
        }
    }

    void open_list(int len) {
        // Do NOT call base — suppress 16-byte length write
    }

    virtual void open_tag(int tag, const std::string &name) {
        if (state == s_array_elem) {
            int128_t type_code = tag + 1;
            setn(type_code, 1);  // write 1-byte type code
            // ... write flags, length ...
        }
    }
};
```

### State Transitions

| Callback | Typical Transition |
|----------|-------------------|
| `set()` | Current field done → next field |
| `close_list()` | Array section done → next section |
| `close_tag()` | Variant element done → back to array state |
| `open_list_elem()` | Prepare for next array element |

## Common Pitfalls

### 1. Signature Mismatch (Most Common)

<anti_pattern>
```cpp
// WRONG — does NOT override base class
virtual void set(int128_t &res) { ... }  // by-reference
```
</anti_pattern>

<example>
```cpp
// CORRECT — overrides base class
virtual void set(int128_t res) { ... }   // by-value
```
</example>

When both exist, C++ dispatches `set(val)` to the by-value base class version, which writes 16 bytes.

### 2. Missing open_list Override

<anti_pattern>
```cpp
// Base class writes 16-byte array length — WRONG for protocols
void open_list(int len) { set((int128_t)len); }
```
</anti_pattern>

<example>
```cpp
// Override with no-op — protocol handles field boundaries via state machine
void open_list(int len) { /* suppress base */ }
```
</example>

### 3. Missing open_tag(int, string) Override

The deserialization `open_tag(vector<string>)` does NOT shadow the serialization `open_tag(int, string)`. Both overloads must be implemented:

```cpp
// Serialization path — called by generated __ser code
virtual void open_tag(int tag, const std::string &name) {
    // Write protocol-specific variant header
}

// Deserialization path — called by generated __deser code
virtual int open_tag(const std::vector<std::string> &tags) {
    // Read bytes, return variant index
}
```

### 4. Uninitialized Locals in setn

<anti_pattern>
```cpp
int128_t len_res;
setn(len_res, 1);  // WRONG — writes garbage from uninitialized stack
```
</anti_pattern>

<example>
```cpp
int128_t len_res = computed_value;
setn(len_res, 1);  // CORRECT — writes the computed value
```
</example>

### 5. State Not Reached Before Array Elements

If `set()` for a scalar field transitions to state X, but the array's `open_list_elem()` fires before `set()` completes the transition, array elements are processed in the wrong state. Verify the callback order matches the state machine's expected sequence.

## Debugging Checklist

1. Add `std::cerr << "state=" << state` in every callback to trace the sequence
2. Check generated C++ for `__ser<YourStruct>` to see exact callback order
3. Verify `set()` signature matches base class (by-value, not by-reference)
4. Check that `open_list(int)` and `open_tag(int, string)` are overridden
5. Compare `header_length` in the Ivy model with actual bytes written (count `setn` calls)
6. Use `tshark` to decode the pcap and compare with expected wire format
