# ivy_compile -- Result Renderer

## Input Fields
Returns: status (success/failure), output_binary, duration_s, errors (if any).

## Default
- Success: "Compiled {file} -> {output_binary} ({duration_s}s)"
- Failure: "Compilation failed: {error_message}"

## verify
- Success: "Compiled: {output_binary} ({duration_s}s)" -- advance immediately.
- Failure: Show error with file:line, suggest switching to diagnose phase.

## build
- Success: "Layer compiled: {file} -> {output_binary}"
- Failure: "Layer compilation failed. Fix before proceeding to next layer."

## review
- Not typically used in review. Default format.

## triage
- Success: "ivy_compile: OK"
- Failure: "ivy_compile: FAIL -- {error_message}"
