---
name: nct-scaffold
description: Scaffold a new protocol or test specification from templates
arguments:
  - name: type
    description: What to scaffold - "protocol" for new protocol from 14-layer template, "test" for new test specification
    required: true
  - name: protocol
    description: Protocol abbreviation (e.g., "quic", "coap", "bgp")
    required: false
  - name: role
    description: Test role (for type=test) - "client", "server", "mim", or "attacker"
    required: false
  - name: name
    description: Test name suffix (for type=test) or protocol full name (for type=protocol)
    required: false
  - name: preset
    description: "Layer preset: minimal (7 core layers), full (all 14), security (minimal + NACT). If omitted, interactive layer selection."
    required: false
---
<!-- MODE: DEEP — Invokes ivy-workflow-orchestrator starting at Phase 1 -->

<HARD-GATE>
Before scaffolding, invoke the ivy-workflow-orchestrator skill.
Complete Phase 1 (Explore) and Phase 2 (Plan) with user approval
before creating any files.
</HARD-GATE>

Scaffold a new protocol or test specification from templates.

## Instructions

### If type="protocol": Scaffold a New Protocol

#### Step 1: Gather Protocol Information (Gate)

Reference the `interaction-patterns` skill for checkpoint format details.

If the `protocol` argument is not provided, use a **Gate checkpoint** with structured options:
- Ask: "What protocol are you scaffolding?"
  - **Protocol name**: Full name (e.g., "Constrained Application Protocol")
  - **Protocol abbreviation**: Short name used in file naming (e.g., "coap")
- Do NOT proceed until both values are confirmed.

#### Step 2: Select Layers (Gate / Inform-and-Continue)

**Preset handling**: If the `preset` argument is provided, use **Inform-and-Continue**: "Using '{preset}' preset ({N} layers). Proceeding to directory creation." Skip interactive selection and use these predefined layer sets:
- `minimal` → Layers 1 (Types), 4 (Frame), 5 (Packet), 7 (Connection), 10 (Entity Defs), 11 (Entity Behavior), 12 (Shims) — 7 layers
- `full` → All 14 layers
- `security` → Minimal + 3 (Security), 9 (Error Handling), 13 (Serialization) — 10 layers

If `preset` is not provided, use a **Gate checkpoint** with multi-choice format. Present the 14-layer template and ask which layers to scaffold. Recommend a preset based on context: "I recommend '{preset}' based on {reason}. Adjust?" Suggest all 14 by default but allow subset selection:

**Core Protocol Stack (recommended: all):**
1. Type Definitions (`{prot}_types.ivy`)
2. Application (`{prot}_application.ivy`)
3. Security/Handshake (`{prot}_security.ivy`)
4. Frame/Message (`{prot}_frame.ivy`)
5. Packet (`{prot}_packet.ivy`)
6. Protection (`{prot}_protection.ivy`)
7. Connection/State (`{prot}_connection.ivy`)
8. Transport Parameters (`{prot}_transport_parameters.ivy`)
9. Error Handling (`{prot}_error_code.ivy`)

**Entity Model (recommended: all):**
10. Entity Definitions (`ivy_{prot}_client.ivy`, `ivy_{prot}_server.ivy`)
11. Entity Behavior (`ivy_{prot}_client_behavior.ivy`, `ivy_{prot}_server_behavior.ivy`)
12. Shims (`{prot}_shim.ivy`)

**Infrastructure (recommended: all):**
13. Serialization/Deserialization (`{prot}_ser.ivy`, `{prot}_deser.ivy`)
14. Utilities (`{prot}_byte_stream.ivy`, `{prot}_file.ivy`, `{prot}_time.ivy`)

**Minimal viable set** (if user wants to start small): Layers 1, 4, 5, 7, 10, 11, 12

#### Step 3: Create Directory Structure

Use Claude's `Write` tool to create each file. The directory structure:

```
protocol-testing/{prot}/
|-- {prot}_stack/
|-- {prot}_entities/
|-- {prot}_shims/
|-- {prot}_utils/
+-- {prot}_tests/
    |-- server_tests/
    |-- client_tests/
    +-- mim_tests/
```

#### Step 4: Populate Template Stubs

For each selected layer, create a file with this template structure:

```ivy
#lang ivy1.7

# {Layer Name} for {Protocol Full Name}
#
# This file defines {layer purpose description}.
# Reference: {relevant RFC section if known}

# [PLACEHOLDER] Define type identifiers, bit vectors, and enumerations for {prot}
```

For entity definitions:
```ivy
#lang ivy1.7

include {prot}_types
include {prot}_connection

# {Role} entity for {Protocol Full Name}
#
# This file defines the {role} participant instance.
```

For test files, create a base test:
```ivy
#lang ivy1.7

include order
include file
include ivy_{prot}_shim_client
include ivy_{prot}_client_behavior

after init {
    # [PLACEHOLDER] Initialize sockets, TLS, transport parameters
}

# [PLACEHOLDER] Export actions for test mirror generation
# export frame.*.handle
# export packet_event

export action _finalize = {
    # [PLACEHOLDER] Add end-state verification
    # require is_no_error;
}
```

#### Step 4b: Confirm Before Writing (Gate)

Before creating any files, use a **Gate checkpoint** to confirm:
- State: "I'll create {N} files in `protocol-testing/{prot}/`. Here's the file list:"
- Show the full list of files to be created.
- Ask: "Proceed with creation? (yes / adjust layers / cancel)"
- Do NOT write any files until the user confirms.

#### Step 5: Report

Show what was created:
```
## Protocol Scaffold Created: {Protocol Name} ({prot})

### Files Created
{List all created files with their layer descriptions}

### Next Steps
1. Start with `{prot}_types.ivy` -- define identifiers, bit vectors, enumerations
2. Build up through frame/packet/connection layers
3. Define entity roles and behavioral constraints
4. Write test specifications
5. Use `/nct-check` to verify as you go
```

#### Step 6: Add Patterns (Optional — Gate)

After creating the directory structure, use a **Gate checkpoint** with structured options to ask the user which formal model patterns to add:

> "Would you like to add formal model patterns to your new protocol? Available patterns:
> - **variants**: PDU type hierarchy (recommended - start here)
> - **entity**: Protocol participants (client/server or speaker/peer)
> - **serdes**: Wire-format serialization (binary or JSON)
> - **monitors**: Behavioral constraints (before/after)
> - **shim**: Network I/O bridge (UDP or TCP)
> - **module**: Parameterized reusable components
> - **all**: Add all patterns in dependency order
>
> Type the pattern names separated by commas, or 'skip' to create empty directories."

If the user selects patterns, invoke `/nct-add-pattern` for each one, following dependency order:
1. variants (no dependencies)
2. entity (no dependencies)
3. module (no dependencies)
4. serdes (needs variants)
5. monitors (needs variants)
6. shim (needs serdes + entity)

---

### If type="test": Scaffold a New Test Specification

#### Step 1: Gather Test Information

If arguments are not provided, ask the user for:
- **Protocol**: Which protocol to create a test for (e.g., quic, coap, bgp)
- **Role**: Which role the test targets -- client, server, mim, or attacker
- **Test name**: A descriptive name for the test variant (e.g., "stream", "migration", "connection_close")

#### Step 2: Determine File Location and Name

Based on the role, determine:
- **server** test -> `protocol-testing/{prot}/{prot}_tests/server_tests/{prot}_server_test_{name}.ivy`
  - Ivy acts as client, tests server IUT
- **client** test -> `protocol-testing/{prot}/{prot}_tests/client_tests/{prot}_client_test_{name}.ivy`
  - Ivy acts as server, tests client IUT
- **mim** test -> `protocol-testing/{prot}/{prot}_tests/mim_tests/{prot}_mim_test_{name}.ivy`
  - Ivy acts as man-in-the-middle
- **attacker** test -> `protocol-testing/apt/apt_tests/server_attacks/{prot}_attacker_test_{name}.ivy`
  - NACT attack test

#### Step 3: Check for Base Test

Check if a base test file exists for this protocol and role:
- `{prot}_server_test.ivy` for server tests
- `{prot}_client_test.ivy` for client tests

Use Claude's `Glob` tool to search. If a base test exists, the new test should include it.

#### Step 4: Create Test File

Use Claude's `Write` tool to create the test file.

**If base test exists** (variant pattern):
```ivy
#lang ivy1.7

include {prot}_{opposing_role}_test

# Test: {test_name}
# Role: Ivy acts as {opposing_role}, testing {role} IUT
# Purpose: {ask user or infer from name}

# Weight attributes to bias test generation toward relevant actions
# attribute frame.{relevant}.handle.weight = "5"

# Additional exported actions for this variant (if any)
# export frame.{specific}.handle

# Additional _finalize checks for this variant (if any)
# after _finalize {
#     require {variant_specific_property};
# }
```

**If no base test exists** (full template):
```ivy
#lang ivy1.7

include order
include file
include ivy_{prot}_shim_{opposing_role}
include ivy_{prot}_{opposing_role}_behavior

# Test: {test_name}
# Role: Ivy acts as {opposing_role}, testing {role} IUT

after init {
    # Initialize network sockets
    # sock := net.open(endpoint_id.{opposing_role}, {opposing_role}.ep);

    # Initialize TLS
    # {opposing_role}.set_tls_id(0);
    # var extns := tls_extensions.empty;
    # extns := extns.append(make_transport_parameters);
    # call tls_api.upper.create(0, false, extns);
}

# Export actions for test mirror generation
# export frame.ack.handle
# export frame.stream.handle
# export frame.crypto.handle
# export packet_event
# export {opposing_role}_send_event

# End-state verification
export action _finalize = {
    # require is_no_error;
    # require conn_total_data(the_cid) > 0;
}
```

Note on role inversion: if testing a **server**, the opposing role (what Ivy plays) is **client**, and vice versa.

#### Step 5: Report

```
## Test Specification Created

**File:** {file_path}
**Protocol:** {protocol}
**Testing:** {role} IUT (Ivy acts as {opposing_role})
**Variant:** {test_name}

### Next Steps
1. Edit the test file to add specific exports and weight attributes
2. Add variant-specific _finalize checks if needed
3. Use `/nct-check {file_path}` to verify formal properties
4. Use `/nct-compile {file_path}` to build the test executable
```

**IMPORTANT**: Use Claude's `Write` tool to create files and Claude's `Glob` tool to find files. Do NOT use Bash file operations.

See the `specification-patterns` skill for the 14-layer template.
