---
name: nct-new-protocol
description: Interactively scaffold a new protocol from the 14-layer template
arguments:
  - name: name
    description: Protocol name (e.g., "coap", "mqtt", "ssh")
    required: false
---

Interactively scaffold a new formal protocol specification from the 14-layer template.

## Instructions

### Step 1: Gather Protocol Information

If the `name` argument is not provided, ask the user:
- **Protocol name**: Full name (e.g., "Constrained Application Protocol")
- **Protocol abbreviation**: Short name used in file naming (e.g., "coap")

### Step 2: Select Layers

Present the 14-layer template and ask which layers to scaffold. Suggest all 14 by default but allow subset selection:

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

### Step 3: Create Directory Structure

Use Claude's `Write` tool to create each file. The directory structure:

```
protocol-testing/{prot}/
├── {prot}_stack/
├── {prot}_entities/
├── {prot}_shims/
├── {prot}_utils/
└── {prot}_tests/
    ├── server_tests/
    ├── client_tests/
    └── mim_tests/
```

### Step 4: Populate Template Stubs

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

### Step 5: Report

Show what was created:
```
## Protocol Scaffold Created: {Protocol Name} ({prot})

### Files Created
{List all created files with their layer descriptions}

### Next Steps
1. Start with `{prot}_types.ivy` — define identifiers, bit vectors, enumerations
2. Build up through frame/packet/connection layers
3. Define entity roles and behavioral constraints
4. Write test specifications
5. Use `/nct-check` to verify as you go
```

**IMPORTANT**: Use Claude's `Write` tool to create all files. Do NOT use Bash file operations.
