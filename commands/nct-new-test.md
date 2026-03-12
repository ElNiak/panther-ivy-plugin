---
name: nct-new-test
description: Scaffold a new Ivy test specification for a protocol
arguments:
  - name: protocol
    description: Protocol abbreviation (e.g., "quic", "coap", "bgp")
    required: false
  - name: role
    description: Test role - "client", "server", "mim", or "attacker"
    required: false
  - name: name
    description: Test name suffix (e.g., "stream", "migration", "timeout")
    required: false
---

Scaffold a new Ivy test specification file.

## Instructions

### Step 1: Gather Test Information

If arguments are not provided, ask the user for:
- **Protocol**: Which protocol to create a test for (e.g., quic, coap, bgp)
- **Role**: Which role the test targets — client, server, mim, or attacker
- **Test name**: A descriptive name for the test variant (e.g., "stream", "migration", "connection_close")

### Step 2: Determine File Location and Name

Based on the role, determine:
- **server** test → `protocol-testing/{prot}/{prot}_tests/server_tests/{prot}_server_test_{name}.ivy`
  - Ivy acts as client, tests server IUT
- **client** test → `protocol-testing/{prot}/{prot}_tests/client_tests/{prot}_client_test_{name}.ivy`
  - Ivy acts as server, tests client IUT
- **mim** test → `protocol-testing/{prot}/{prot}_tests/mim_tests/{prot}_mim_test_{name}.ivy`
  - Ivy acts as man-in-the-middle
- **attacker** test → `protocol-testing/apt/apt_tests/server_attacks/{prot}_attacker_test_{name}.ivy`
  - NACT attack test

### Step 3: Check for Base Test

Check if a base test file exists for this protocol and role:
- `{prot}_server_test.ivy` for server tests
- `{prot}_client_test.ivy` for client tests

Use Claude's `Glob` tool to search. If a base test exists, the new test should include it.

### Step 4: Create Test File

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

### Step 5: Report

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
