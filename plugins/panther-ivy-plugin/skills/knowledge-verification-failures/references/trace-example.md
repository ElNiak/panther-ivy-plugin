# End-to-End Trace Interpretation Example

A complete worked example of reading a counterexample trace and identifying the fix.

---

<worked_example>

## Scenario

`ivy_verify` fails on `quic_server_test_stream.ivy` with this `counterexample_trace`:

```
Violated assertion (Line 87):
  require stream_data_sent(S)

Execution trace (3 steps):
--------------------------------------------------

  Step 1: quic_connection.open
    conn_seen = true
    cid = 0xABCD
    connected = true

  Step 2: frame.stream.handle
    stream_id = 4
    stream_state = idle  (was: idle)
    bytes_sent = 0

  Step 3: _finalize
    stream_data_sent = false
```

## Diagnosis

1. **Violated assertion**: `require stream_data_sent(S)` at line 87, inside `_finalize`
2. **Step 2 observation**: `stream_state` stays `idle` — it was never transitioned to `open` or `sending`. The `bytes_sent = 0` confirms no data was actually sent.
3. **Root cause**: `frame.stream.handle` fires but does not update `stream_data_sent` or `stream_state`. The `after` block for `frame.stream.handle` is missing the state update, or the `before` block does not require `f.length > 0` to ensure meaningful data.

## Investigation

Use LSP `hover` on the `stream_data_sent` symbol to get its type info, then `findReferences` to see where it is set.

This reveals `stream_data_sent` is set in `after frame.stream.handle` only when `f.length > 0`, but no `before` guard requires `f.length > 0` during test generation.

## Fix

Add a generation guard to ensure the test mirror only generates meaningful stream frames:

```ivy
before frame.stream.handle(f:frame.stream, scid:cid, dcid:cid, e:quic_packet_type) {
    if _generating {
        require f.length > 0;                 # Ensure non-empty stream data
        require stream_state(f.id) = open;    # Ensure stream is open
    }
}
```

After applying the fix, re-run `ivy_verify` to confirm the counterexample is resolved.

</worked_example>
