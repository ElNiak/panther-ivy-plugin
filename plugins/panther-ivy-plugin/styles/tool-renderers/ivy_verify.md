# ivy_verify -- Result Renderer

## Input Fields
The tool returns: isolate, status (pass/fail), clause_count, duration_s, errors (list of {file, line, message, isolate}).

## Default (no workflow active)
- Pass: "PASS: {isolate} verified ({clause_count} clauses, {duration_s}s)"
- Fail: "FAIL: {isolate} at {file}:{line} -- {message}"

## verify
- Pass: "PASS: {isolate} ({clause_count} clauses, {duration_s}s)"
- Fail: Numbered list of all errors. Include context hint: "See {file}:{line}."
- Summary line: "{pass_count}/{total} isolates passed."

## build
- Pass: "Layer verified: {isolate} PASS"
- Fail: "Layer verification failed -- switching to verify workflow for diagnosis."
- Only show the isolate relevant to the current build layer.

## review
- Pass/fail as table row: | {isolate} | {status} | {clause_count} | {duration_s}s |
- Aggregate into a table when multiple isolates verified in sequence.

## triage
- Pass: "ivy_verify: OK"
- Fail: "ivy_verify: FAIL -- {error_count} error(s). Run verify workflow for details."
