# QUIC Canonical Example

This reference provides the QUIC protocol walkthrough as the canonical NCT implementation.
Loaded on demand by the nct-methodology skill.

## Overview

The QUIC model (`protocol-testing/quic/`) is the most complete NCT implementation with 200+ files and 50+ test variants covering:

- Stream handling
- Connection close
- Retry
- Migration
- Transport parameter validation
- Error conditions
- 0-RTT
- Congestion control
- Loss recovery
- Version negotiation
- Timeout handling

## Directory Layout

```
protocol-testing/quic/
├── quic_stack/           # Core protocol model (layers 1-9)
│   ├── quic_types.ivy           # Layer 1: Types
│   ├── quic_frame.ivy           # Layer 4: Frame definitions
│   ├── quic_packet.ivy          # Layer 5: Packet structure
│   ├── quic_protection.ivy      # Layer 6: Encryption
│   ├── quic_connection.ivy      # Layer 7: Session lifecycle
│   ├── quic_transport_parameters.ivy  # Layer 8: Transport params
│   └── quic_error_code.ivy      # Layer 9: Error taxonomy
├── quic_entities/        # Entity definitions + behavior (layers 10-12)
│   ├── ivy_quic_client.ivy
│   ├── ivy_quic_server.ivy
│   └── ivy_quic_client_server_behavior.ivy
├── quic_shims/           # Implementation bridge (layer 12)
│   ├── quic_shim_client.ivy
│   └── quic_shim_server.ivy
├── quic_utils/           # Serialization + utilities (layers 13-14)
│   ├── quic_ser.ivy
│   └── quic_deser.ivy
└── quic_tests/
    ├── server_tests/     # Ivy=client, tests server IUT
    │   ├── quic_server_test.ivy         # Base test spec
    │   └── quic_server_test_*.ivy       # Variants (stream, retry, etc.)
    ├── client_tests/     # Ivy=server, tests client IUT
    │   └── quic_client_test.ivy
    └── mim_tests/        # Man-in-the-middle tests
```

## Canonical Entry Point

Examine `quic_server_test.ivy` as the canonical test structure example:

1. Includes the QUIC stack, shim (client role), and behavioral constraints
2. Initializes sockets and TLS in `after init`
3. Exports frame handlers and `packet_event` for test mirror generation
4. Exports `_finalize` for end-state verification

## Test Variants

Each variant file includes the base test and adds/modifies:
- Additional `export` declarations for specific frame types
- `attribute` weight adjustments to bias test generation
- Additional `_finalize` requirements for scenario-specific checks

## Role Inversion in Practice

| Test File | What It Tests | Ivy Plays |
|-----------|--------------|-----------|
| `quic_server_test_*.ivy` | Server IUT | Client |
| `quic_client_test_*.ivy` | Client IUT | Server |
| `quic_mim_test_*.ivy` | Both (MIM) | Man-in-the-middle |

## Coverage Tool Usage

For QUIC-scoped coverage:
```
ivy_coverage(mode="stats", test_file="quic/quic_tests/server_tests/quic_server_test.ivy")
ivy_coverage(mode="gaps", test_file="quic/quic_tests/server_tests/quic_server_test.ivy")
ivy_coverage(mode="matrix", test_file="quic/quic_tests/server_tests/quic_server_test.ivy")
```
