# Ivy Syntax Examples — Test Specs & RFC Annotations

## Test Specification Patterns

### Test Specification Structure

Every test specification follows this pattern:
<example>
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
</example>

### Key Components

#### Includes
Order matters. Critical includes:
- **Shim** (`ivy_{prot}_shim_{role}`) -- bridges formal model to implementation
- **Entity behavior** (`ivy_{prot}_{role}_behavior`) -- encodes RFC requirements

#### Initialization (`after init`)
Opens network sockets, sets TLS identifiers, creates transport parameter extensions, initializes TLS/security layer.

#### Exported Actions
`export` declarations tell the test mirror which actions to generate randomly. Z3/SMT ensures generated actions satisfy all `before` clause constraints.

#### Export Design Decisions

- **Handle actions for composite messages**: Export sub-element builder actions (e.g., `frame.path_attribute.handle`) when the protocol requires composite messages built from multiple parts. Guard these with `if _generating { ... }` in their `before` clause. See `generator-mechanics.md` for the frame-queuing pattern.
- **Auto-send pattern for message events**: Prefer single-action message events that construct and send in one step. Two-step patterns (create then send) cause generator starvation because random selection rarely picks both in sequence. See `generator-mechanics.md`.
- **Do not export timer events**: Exporting timer actions (e.g., `timeout_event`, `keepalive_timer`) lets the generator spend iterations on non-message actions, starving protocol traffic. Handle timers internally via shim callbacks or `after init` instead.
- **Empty array constraints**: Use `.end = 0` instead of `= arr.empty` when constraining arrays to be empty in `before` guards. The `.end = 0` form is more reliable for Z3 solving.

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
<example>
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
</example>

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
