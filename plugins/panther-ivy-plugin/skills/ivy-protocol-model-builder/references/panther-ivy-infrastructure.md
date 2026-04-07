# panther_ivy Infrastructure Reference

## Ivy Compilation Pipeline

1. **`ivy_check model.ivy`** (or `ivy_verify` MCP tool) — validates the model for type correctness and well-formedness. Fast (seconds). No binary produced. Use during Phases 3-4 for quick feedback.

2. **`ivyc target=test test_iters=100 model.ivy`** (or `ivy_compile` MCP tool) — translates the Ivy model to C++, then compiles the C++ into a native binary. Slow (minutes, because of C++ compilation). The binary lands in `$PYTHON_IVY_DIR/ivy/include/1.7/` with the test file's name. Use from Phase 4 onward.

3. **Run the binary** — the compiled binary takes command-line arguments for network addresses, ports, random seed, etc.:
   ```bash
   ./{proto}_{role}_test seed=42 server_addr=0x0a000001 server_port=4443 \
       client_addr=0x0a000002 client_port=4987
   ```

4. **Test output** — the binary prints event traces (actions being called) to stdout. On success, it terminates normally after exhausting iterations. On failure, it prints an assertion error with the Ivy source file and line number:
   ```
   FAIL: require at {proto}_message.ivy:42 (constraint violated)
   ```

## MCP Tool Equivalents

Prefer MCP tools over CLI for structured output and integration with other panther-ivy-plugin features.

| CLI Command | MCP Tool | Advantage |
|---|---|---|
| `ivy_check` | `ivy_verify` | Structured output, isolate support |
| `ivyc target=test` | `ivy_compile(target="test")` | Structured output |
| `ivy_show` | `ivy_model_info` | Model introspection |
| — | `ivy_diagnostics(mode="structural")` | Fast structural check (milliseconds) |
| — | `ivy_coverage(mode="gaps")` | Find uncovered requirements |
| — | `ivy_coverage(mode="matrix")` | Requirement-to-assertion mapping |
| — | `ivy_patterns(mode="check")` | Layer/pattern completeness |

## Built-in Modules

The panther_ivy infrastructure provides these modules on the Ivy include path:

| Module | Provides | Used In |
|---|---|---|
| `ip` | `ip.endpoint`, `ip.addr`, `ip.port`, `ip.udp`, `ip.lo`, `ip.ivy` (interface types) | Entity setup |
| `net` | `net.open`, `net.send`, `net.recv`, `net.socket` | Shim I/O |
| `tls_api` | `tls_api.id`, `tls_api.upper.create`, TLS handshake, key exchange | Crypto-enabled protocols |
| `prot` | `prot.encrypt`, `prot.decrypt`, `prot.arr` (instantiated from protection module) | Packet protection |
| `serdes` | Serialization/deserialization framework | `{proto}_utils/` ser/deser |
| `collections` | Sequences, arrays, maps (included transitively) | Data structures |
| `order` | Ordered types, comparison | Sorting, ranges |
| `random_value` | Nondeterministic value generation (`random_stream_pos`, `random_microsecs`) | Config, behavioral specs |
| `byte_stream` | Byte array utilities | Serialization helpers |
| `file` | File I/O for logging | Test output |
| `time_api` | `c_timer`, `chrono_timer`, `now_millis_last_bp`, timestamps | Timeout testing |
| `{proto}_locale` | Network locale setup (per-protocol, created in `{proto}_utils/`) | Entity wiring |

## Include Path Resolution

Modules resolve from the Ivy include path (`$PYTHON_IVY_DIR/ivy/include/1.7/`). The working directory must be set correctly for protocol-specific includes to resolve. When using MCP tools, the `relative_path` parameter handles this automatically.

## File Naming Convention

- **Stack/protocol files**: `{proto}_*.ivy` (e.g., `quic_packet.ivy`, `quic_frame.ivy`). Model the protocol itself.
- **Infrastructure/entity files**: `ivy_{proto}_*.ivy` (e.g., `ivy_quic_server.ivy`, `ivy_quic_shim_client.ivy`). Ivy testing infrastructure wrapping the protocol model.
