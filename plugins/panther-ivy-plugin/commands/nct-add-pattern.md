---
name: nct-add-pattern
description: Add a formal model pattern to a protocol specification
arguments:
  - name: protocol
    description: Protocol name (e.g., quic, bgp, minip, mark)
    required: true
  - name: pattern
    description: "Pattern to add: serdes, variants, monitors, shim, module, entity, or all"
    required: true
  - name: wire_format
    description: "Wire format for serdes pattern: binary (default) or json"
    required: false
  - name: role_type
    description: "Role type for entity pattern: asymmetric (default) or symmetric"
    required: false
---

# Add Pattern to Protocol

## Step 1: Validate Protocol Directory

Check that the protocol directory exists under `protocol-testing/`:
- Standard path: `protocol-testing/{protocol}/`
- APT path: `protocol-testing/apt/apt_protocols/{protocol}/`

If neither exists, ask the user if they want to create it first with `/nct-scaffold type=protocol`.

## Step 2: Detect Current State

Use the `ivy_patterns` MCP tool to check what patterns already exist:

```
ivy_patterns(mode="analyze", protocol="{protocol}")
```

Report which patterns are already present and which are missing.

## Step 3: Resolve Dependencies

Patterns have dependencies. Check and add prerequisites first:

| Pattern | Depends On |
|---------|-----------|
| serdes | variants |
| monitors | variants |
| shim | serdes, entities |
| variants | (none) |
| module | (none) |
| entity | (none) |

If adding "all", follow this order: variants → entity → module → serdes → monitors → shim

## Step 4: Load and Customize Template

For the requested pattern, load the template from `protocol-testing/patterns/`:

### serdes
- `wire_format=binary`: Use `serdes/binary_ser_template.ivy` and `serdes/binary_deser_template.ivy`
- `wire_format=json`: Use `serdes/json_ser_template.ivy` and `serdes/json_deser_template.ivy`
- Replace `{prot}` with protocol name, `{PROT}` with uppercase

### variants
- Use `variants/variant_frame_template.ivy`
- Ask the user for variant/message type names

### monitors
- Use `monitors/before_after_template.ivy`
- Optionally add `monitors/finalize_template.ivy` and `monitors/export_weight_template.ivy`

### shim
- Ask: UDP or TCP transport?
- Use `shims/shim_udp_template.ivy` or `shims/shim_tcp_template.ivy`

### module
- Use `modules/parameterized_module_template.ivy`

### entity
- `role_type=asymmetric`: Use `entities/entity_role_pair_template.ivy`
- `role_type=symmetric`: Use `entities/entity_symmetric_template.ivy`

## Step 5: Write Files

Use Claude's `Write` tool to create the generated files in the appropriate subdirectory:
- `{protocol}/{protocol}_stack/` for variants, modules
- `{protocol}/{protocol}_utils/` or `{protocol}/{protocol}_stack/` for serdes
- `{protocol}/{protocol}_entities/` for entities, monitors
- `{protocol}/{protocol}_shims/` for shims

## Step 6: Verify

Run `ivy_lint` on the generated files to verify structural correctness.

## Step 7: Report

Tell the user:
1. What files were created
2. What placeholders remain to be filled in (marked with `TODO` or `{...}`)
3. Suggested next steps (e.g., "Define your message types", "Add field constraints")
4. Cross-references to the pattern-library skill for detailed documentation

See the `specification-patterns` skill for pattern dependencies.
