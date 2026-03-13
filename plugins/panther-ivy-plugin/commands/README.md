# Commands

## Overview

This directory contains 5 slash commands for common Ivy formal verification operations within the panther-ivy-plugin for Claude Code. All commands use the `ivy-tools` MCP tools for verification/compilation/model-info and Claude's native tools (`Grep`, `Read`, `Glob`, `Write`) for code navigation and file operations -- they do NOT invoke Ivy CLI tools (e.g., `ivy_check`, `ivyc`, `ivy_show`) directly via Bash.

## Command Reference

| Command | Description | Required Args | Optional Args |
|---------|-------------|---------------|---------------|
| `/nct-check` | Run formal verification on an Ivy specification file via ivy-tools | `file` -- path to `.ivy` file | `isolate` -- isolate name to check |
| `/nct-compile` | Compile an Ivy model to a test binary via ivy-tools | `file` -- path to `.ivy` file | `target` -- compilation target (default `"test"`); `isolate` -- isolate name |
| `/nct-model-info` | Display the structure of an Ivy model via ivy-tools | `file` -- path to `.ivy` file | `isolate` -- isolate name to inspect |
| `/nct-scaffold` | Scaffold a new protocol or test specification | `type` -- `"protocol"` or `"test"` | `name` -- protocol/test name; `protocol` -- target protocol (for tests); `role` -- `"client"`, `"server"`, `"mim"`, or `"attacker"` (for tests) |
| `/nct-add-pattern` | Add a formal model pattern to an existing protocol specification | `pattern` -- pattern name (e.g., `"variant"`, `"shim"`, `"monitor"`) | `protocol` -- target protocol; `file` -- target file |

## Detailed Usage

### `/nct-check`

Run formal verification on an Ivy specification file.

**Usage:**

```
/nct-check file=<path> [isolate=<isolate_name>]
```

**Example:**

```
/nct-check file=protocol-testing/quic/quic_stack/quic_packet.ivy
/nct-check file=protocol-testing/quic/quic_stack/quic_connection.ivy isolate=quic_connection_iso
```

**Expected output format:**

- On success (`return_code` 0): a `Verification Result: PASS` report listing the file, isolate (or "all"), and confirmation that isolate assumptions, invariants, and safety properties passed.
- On failure (`return_code` non-zero): a `Verification Result: FAIL` report with parsed error messages from `stderr` and suggested follow-up actions (inspect model info, find failing symbols, check behavior monitors).

**Notes:**

- If no file is provided, the command will prompt for which `.ivy` file to verify.
- Internally calls `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`.

---

### `/nct-compile`

Compile an Ivy model to a test executable.

**Usage:**

```
/nct-compile file=<path> [target=<target>] [isolate=<isolate_name>]
```

**Example:**

```
/nct-compile file=protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream.ivy
/nct-compile file=protocol-testing/quic/quic_tests/server_tests/quic_server_test_stream.ivy target=test isolate=quic_server_test_iso
```

**Expected output format:**

- On success (`return_code` 0): a `Compilation Result: SUCCESS` report showing the file, target, isolate, and a note that the binary is in the `build/` directory. Suggests running via the PANTHER experiment framework and verifying with `/nct-check` before execution.
- On failure (`return_code` non-zero): a `Compilation Result: FAILURE` report with parsed error messages and suggested actions (run `/nct-check` first, inspect file structure, check for missing includes or undefined symbols).

**Notes:**

- If no file is provided, the command will prompt for which `.ivy` file to compile.
- The default compilation target is `"test"` when not specified.
- Internally calls `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile`.

---

### `/nct-model-info`

Display the structure of an Ivy model -- types, relations, functions, actions, invariants, and isolates.

**Usage:**

```
/nct-model-info file=<path> [isolate=<isolate_name>]
```

**Example:**

```
/nct-model-info file=protocol-testing/quic/quic_stack/quic_frame.ivy
/nct-model-info file=protocol-testing/quic/quic_stack/quic_connection.ivy isolate=quic_connection_iso
```

**Expected output format:**

A structured `Model Structure` report organized into sections: Types, Relations, Functions, Actions (with signatures), Invariants, and Isolates. For large models, output is summarized with key counts (e.g., "X types, Y relations, Z actions, W invariants").

**Notes:**

- If no file is provided, the command will prompt for which `.ivy` file to inspect.
- If the model cannot be parsed (`return_code` non-zero), the command suggests using `/nct-check` to diagnose the issue.
- Internally calls `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info`.

---

### `/nct-scaffold`

Scaffold a new protocol model or test specification from templates.

**Usage:**

```
/nct-scaffold type=<protocol|test> [name=<name>] [protocol=<abbr>] [role=<role>]
```

**Example:**

```
/nct-scaffold type=protocol name=coap
/nct-scaffold type=test protocol=quic role=server name=stream
/nct-scaffold type=test protocol=coap role=client name=observe
```

**For `type=protocol`:**

Creates a directory structure under `protocol-testing/{name}/` using the 14-layer template:
- **Core Protocol Stack** (layers 1--9): types, application, security, frame, packet, protection, connection, transport parameters, error handling
- **Entity Model** (layers 10--12): entity definitions, entity behavior, shims
- **Infrastructure** (layers 13--14): serialization/deserialization, utilities

A minimal viable subset (layers 1, 4, 5, 7, 10, 11, 12) is available for users who want to start small.

**For `type=test`:**

Creates a test specification file. Role inversion applies: testing a **server** means Ivy acts as **client**, and vice versa. File placement depends on role:
- `server` -> `protocol-testing/{prot}/{prot}_tests/server_tests/{prot}_server_test_{name}.ivy`
- `client` -> `protocol-testing/{prot}/{prot}_tests/client_tests/{prot}_client_test_{name}.ivy`
- `mim` -> `protocol-testing/{prot}/{prot}_tests/mim_tests/{prot}_mim_test_{name}.ivy`
- `attacker` -> `protocol-testing/apt/apt_tests/server_attacks/{prot}_attacker_test_{name}.ivy`

If a base test file already exists for the protocol/role, the new test includes it (variant pattern); otherwise a full template is generated.

**Notes:**

- If arguments are omitted, the command prompts interactively for each missing value.
- Internally uses Claude's `Write` tool to create files and `Glob` tool to find files.

## Common Workflows

### Verify before commit

Run verification, fix any failures, then verify again until clean:

```
/nct-check file=<path>
# fix reported issues
/nct-check file=<path>
```

### New protocol from scratch

Scaffold the protocol structure, edit the generated stubs, verify incrementally, then compile tests:

```
/nct-scaffold type=protocol name=<prot>
# edit type definitions, frame/packet layers, entity models
/nct-check file=protocol-testing/<prot>/<prot>_stack/<prot>_types.ivy
# continue editing and checking layer by layer
/nct-compile file=protocol-testing/<prot>/<prot>_tests/server_tests/<prot>_server_test.ivy
```

### Add a test variant

Scaffold a new test, customize it, verify, and compile:

```
/nct-scaffold type=test protocol=<prot> role=server name=<variant>
# edit exports, weight attributes, and _finalize checks
/nct-check file=protocol-testing/<prot>/<prot>_tests/server_tests/<prot>_server_test_<variant>.ivy
/nct-compile file=protocol-testing/<prot>/<prot>_tests/server_tests/<prot>_server_test_<variant>.ivy
```

### Explore an existing model

Inspect the model structure, then drill into verification:

```
/nct-model-info file=protocol-testing/quic/quic_stack/quic_connection.ivy
/nct-check file=protocol-testing/quic/quic_stack/quic_connection.ivy isolate=quic_connection_iso
```
