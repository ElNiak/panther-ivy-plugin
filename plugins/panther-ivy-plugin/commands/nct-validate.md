---
name: nct-validate
description: Scenario-based validation of Ivy LSP, MCP tools, hooks, agents, and surface coverage (~75 checks across 5 passes) with cross-validation, interactive review, and optional mutation testing
arguments:
  - name: phase
    description: "Comma-separated passes to run: preflight, scenarios, gapsweep, nonworkflow, interactive. Default: all"
    required: false
  - name: scenario
    description: "Comma-separated scenarios: A, B, C, D, E, F, FX. Default: all in selected passes"
    required: false
  - name: check
    description: "Comma-separated check IDs: P1, A3, B1, FX2, H5, AG1, S1, SR1. Default: all in selected scenarios"
    required: false
  - name: mode
    description: "fast (skip mutations, agents, gap sweep, interactive confirmation) or full (default)"
    required: false
  - name: error-injection
    description: "full = 3 mutation types (header, brace, include). Default: 1 mutation (include only). false = skip all."
    required: false
---
<!-- MODE: HYBRID — fast mode skips orchestrator, full mode aligns with Phase 4 -->

Run a scenario-based validation of the Ivy LSP, MCP tools, plugin hooks, agents, and surface coverage. Unlike `/nct-health` (connectivity), this command checks **correctness** by simulating real user workflows — exploring the model, auditing coverage, debugging failures, editing specs — with cross-validation between tools and interactive manual review.

## Instructions

### Argument Parsing

Parse optional arguments from the user's invocation:

1. **`mode`**: `fast` or `full` (default: `full`).
   - `fast` skips: Scenario D (mutations), Pass 2 (gap sweep), Pass 3 agents (AG1-AG5), Pass 4 interactive confirmation (prints values directly without waiting).
   - `fast` keeps: Pass 0, Scenarios A/B/C/E/F, negative tests (FX1-FX8), hooks, surface, SR1.

2. **`phase`**: If provided, split by comma and map to pass numbers:
   - `preflight` → Pass 0 (always runs as gate regardless of this argument)
   - `scenarios` → Pass 1 (all scenarios + negative tests)
   - `gapsweep` → Pass 2
   - `nonworkflow` → Pass 3 (hooks + surface + agents)
   - `interactive` → Pass 4
   - If omitted, run **all** passes.

3. **`scenario`**: If provided, split by comma. Only run matching scenarios within Pass 1. Pass 0 still runs as gate.
   - Valid values: `A`, `B`, `C`, `D`, `E`, `F`, `FX` (negative tests).

4. **`check`**: If provided, split by comma. Only run checks whose ID matches. Pass 0 still runs as gate.

5. **`error-injection`**: Controls mutation tests in Scenario D.
   - `false` → skip all mutations (D3-D6 become SKIPPED).
   - Default (no arg) → 1 mutation type (bad include insertion).
   - `full` → all 3 mutation types (missing `#lang` header, unmatched brace, bad include).

**Pass dependencies**:
- Pass 0 (pre-flight) **always runs first** when any downstream pass is requested.
- SR1 (self-review) **always runs last** (unless explicitly excluded via `phase` argument).

### General Rules

- For each check: call the specified tool, validate response **structure** (fields present, no stack traces, sane values), record PASS/FAIL/SKIPPED with a 1-2 sentence **reflection** connecting the result to prior checks.
- **No ground truth comparison.** Checks validate structure and sanity only. Actual values are collected for the interactive review table in Pass 4.
- **Never abort early.** If a check fails, record FAIL and continue. If a subsystem is unavailable, mark dependent checks as SKIPPED and continue.
- **Cross-validation**: When a check references a prior result, explicitly compare and note agreement or disagreement.
- Track all results for SR1 (self-review meta-analysis) and Pass 4 (interactive table).

---

## Pass 0: Pre-flight (3 checks)

**Always runs first**, regardless of `phase` argument. Gates all downstream passes.

### P1: LSP process alive

Run via Bash:
```
pgrep -f ivy_lsp
```

- **Structural**: PIDs are returned in the output.
- If PIDs returned: **PASS** — report PID(s).
- If no output or error: **FAIL** — "No ivy_lsp process found."
- **Impact**: All LSP checks in Pass 1 and Pass 3 are SKIPPED.

### P2: MCP server health

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- **Structural**: Response contains `ivy_check: true`, `ivyc: true`, `ivy_show: true`.
- If all three capability flags are true: **PASS**.
- If any flag is false or tool errors: **FAIL**.
- **Impact**: All MCP tool checks in Pass 1 and Pass 3 are SKIPPED.

### P3: LSP responding

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line 1, character 0 (resolve to absolute path in the detected workspace).

- **Structural**: Any response received (even empty hover content).
- If any response: **PASS** — LSP is responding.
- If timeout or error: **FAIL**.
- **Impact**: All LSP checks in Pass 1 are SKIPPED.

---

## Pass 1: Scenarios (42 checks: 34 scenario + 8 negative)

All checks run **sequentially**. Each check includes a reflection that references prior results. Skip entire scenarios if their gate (P1, P2, or P3) failed.

### Scenario A: Exploration — "I'm new, show me the QUIC model" (8 checks)

Simulates a user opening a spec file and navigating through the model to understand its structure.

#### A1: Model info (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: Response present, contains type or action information.
- **Reflection**: This is the entry point — note what types and actions the model reports.
- **Record**: List of types and actions reported (for cross-validation with A2).
- If valid response with type/action data: **PASS**. Otherwise: **FAIL** — "model_info returned no type/action data."

#### A2: Document symbols (quic_types)

Use the `LSP` tool to request `documentSymbol` on `quic/quic_stack/quic_types.ivy`.

- **Structural**: Returns a list; each entry has `name` and `range` fields; line numbers are non-negative.
- **Reflection**: Compare symbol names with A1 types — do they overlap? The LSP symbol list should include the types reported by model_info.
- **Record**: Full symbol list with names and line numbers.
- If valid list with symbols: **PASS**. Otherwise: **FAIL** — "documentSymbol returned empty or malformed list."

#### A3: Hover on type (cid)

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at the line where `cid` appears in the A2 symbol list (use the line number from A2's results). If A2 did not return `cid`, use line 30, character 6 as a reasonable default.

- **Structural**: Response has `contents` field, content is non-empty.
- **Reflection**: Does the hover mention a type from A2's symbol list? Does it identify `cid`?
- **Record**: Hover content text and the file + line used.
- If hover content mentions `cid` or a type definition: **PASS**. Otherwise: **FAIL** — "Hover returned empty or unrelated content."

#### A4: Go-to-definition (cid)

Use the `LSP` tool to request `goToDefinition` on `quic/quic_stack/quic_types.ivy` at the same position used for A3.

- **Structural**: Returns a result with `uri` and `range` fields; target file exists.
- **Reflection**: Does the definition target point to `quic_types.ivy`? For a type definition, goToDefinition from the definition itself should resolve to the same file.
- **Cross-validation**: Target file consistent with A2's symbol location for `cid`.
- **Record**: Target file and line number.
- If valid definition location returned: **PASS**. Otherwise: **FAIL** — "goToDefinition returned no result."

#### A5: Find references (cid)

Use the `LSP` tool to request `findReferences` on `quic/quic_stack/quic_types.ivy` at the same position used for A3.

- **Structural**: Returns more than 1 reference location across more than 1 file.
- **Reflection**: `cid` is a fundamental type used throughout the QUIC model — expect widespread usage across multiple files.
- **Record**: Reference count and list of unique files.
- If multiple references across multiple files: **PASS**. Otherwise: **FAIL** — "findReferences returned too few results for a fundamental type."

#### A6: Workspace symbol search (cid)

Use the `LSP` tool to request `workspaceSymbol` with query `cid`.

- **Structural**: Returns at least 1 result with `name` and `location` fields.
- **Reflection**: The workspace symbol search should find `cid` in `quic_types.ivy`.
- **Cross-validation**: Location matches A3 hover position and A4 definition target. All three (A3, A4, A6) should agree on which file contains `cid`.
- **Record**: Result list with file locations.
- If result found: **PASS**. Otherwise: **FAIL** — "workspaceSymbol returned no results for cid."

#### A7: Include graph (quic_connection)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with:
- `relative_path`: `quic/quic_stack/quic_connection.ivy`

- **Structural**: Non-empty include list; all `resolved_path` values are non-null.
- **Reflection**: Note the include count. Check if `quic_types` appears in the include list — it should, since `cid` (explored in A1-A6) is defined there and used by the connection module.
- **Record**: Include count and list of included module names.
- If non-empty include list with resolved paths: **PASS**. Otherwise: **FAIL** — "Include graph returned empty or has unresolved paths."

#### A8: Symbol query (cid)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `cid`
- `protocol`: `quic`

- **Structural**: `found: true`; response has `file` and `line` fields.
- **Reflection**: This is the MCP equivalent of the LSP hover/definition checks — does it agree?
- **Cross-validation**: File and line must be consistent with A3 (hover), A4 (goToDefinition), and A6 (workspaceSymbol). This is a **4-way agreement check** on `cid` location: A3 + A4 + A6 + A8 must all point to the same file.
- **Record**: File path and line number.
- If found with file and line: **PASS**. Otherwise: **FAIL** — "ivy_query did not find cid."

---

### Scenario B: Coverage Audit — "What's our RFC coverage?" (6 checks)

Simulates a user reviewing requirement coverage and finding gaps.

#### B1: Coverage stats (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `stats`
- `relative_path`: `quic/`

- **Structural**: `total > 0`; level breakdown present with categories (MUST, MUST_NOT, SHOULD, SHOULD_NOT, MAY).
- **Self-consistency**: Verify that `total = MUST + MUST_NOT + SHOULD + SHOULD_NOT + MAY`. If the sum does not match the reported total, note the discrepancy.
- **Record**: Total count and per-level breakdown.
- If total > 0 and level breakdown present: **PASS**. Otherwise: **FAIL** — "Coverage stats returned zero total or missing breakdown."

#### B2: Coverage gaps (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `gaps`
- `protocol`: `quic`

- **Structural**: Returns a list (may be empty if all requirements are covered).
- **Cross-validation**: Is there a meaningful relationship with B1 totals? If B1 reports uncovered requirements, B2 should return a non-empty list.
- **Record**: Gap count and first few gap identifiers.
- If list returned (even empty): **PASS**. Otherwise: **FAIL** — "Coverage gaps returned error."

#### B3: Query first gap from B2

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: First uncovered symbol or requirement identifier from B2's results.

**Skip if B2 returned an empty gaps list** (no uncovered requirements to investigate).

If B2 returns requirement IDs rather than symbol names, use the requirement's associated file or action as the query target instead.

- **Structural**: Response present — `found: true` or graceful `not found` are both valid outcomes.
- **Reflection**: Can we navigate to where this gap lives? This simulates a user drilling into a coverage gap to understand it.
- **Record**: Query result (found/not found, file, line if available).
- If graceful response: **PASS**. Otherwise: **FAIL** — "ivy_query crashed on gap symbol."

#### B4: Coverage matrix (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `matrix`
- `relative_path`: `quic/`

- **Structural**: Non-empty requirement-to-assertion mapping returned.
- **Cross-validation**: Is the covered count from the matrix consistent with B1 stats? The matrix should account for the same total reported in B1.
- **Record**: Covered requirement count from matrix.
- If non-empty matrix returned: **PASS**. Otherwise: **FAIL** — "Coverage matrix returned empty."

#### B5: Extract requirements (sample RFC text)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_extract_requirements` with:
- `rfc_text`: `"An endpoint MUST NOT send data on a stream without ensuring that the peer is willing to accept it. An endpoint SHOULD limit the amount of data it sends based on initial limits."`

- **Structural**: Returns parsed requirements with categories (MUST, SHOULD, MAY, etc.).
- **Reflection**: Does extraction produce MUST/SHOULD/MAY categories matching RFC 2119 keyword usage? The sample text contains one MUST NOT and one SHOULD.
- **Record**: Extracted requirement categories and count.
- If requirements returned with categories: **PASS**. Otherwise: **FAIL** — "extract_requirements returned empty or no categories."

#### B6: Model summary (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_summary` with:
- `test_file`: `quic/`

- **Structural**: Non-empty result with per-action data.
- **Cross-validation**: Action count > 0. Does the scope relate to B1 coverage (both scoped to quic)?
- **Record**: Action count.
- If non-empty summary returned: **PASS**. Otherwise: **FAIL** — "Model summary returned empty."

---

### Scenario C: Debug Verification Failure — "ivy_verify failed, now what?" (5 checks)

Simulates the debugging workflow after a verification failure. Uses the known error in quic_types.ivy.

**Branching logic**: C1 determines the path. If verify fails (expected for quic_types.ivy), C2-C5 trace the error. If verify succeeds (the known error was fixed), SKIP C2-C5 with reason "no failure to debug — verification succeeded."

#### C1: Verify (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: Returns a result with `success` field (true or false — both are valid outcomes).
- **Record**: If failure, capture which symbol/line is reported in the error output. If success, record that verification passed.
- **Reflection**: quic_types.ivy is known to have a verification failure. If it succeeds, the model may have been updated.
- If result returned with clear success/failure status: **PASS**. Otherwise: **FAIL** — "ivy_verify returned no result or crashed."
- **Branch**: If `success: true`, SKIP C2-C5 with reason "verification succeeded — no failure to debug."

#### C2: Query error symbol

**Skip if C1 succeeded.**

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: The symbol name from C1's error output.

- **Structural**: `found: true` or graceful not-found response.
- **Reflection**: Can we locate the failing symbol? Does the query agree with verify's error location?
- **Record**: Symbol location (file, line).
- If response present: **PASS**. Otherwise: **FAIL** — "ivy_query crashed on error symbol."

#### C3: Hover on error location

**Skip if C1 succeeded.**

Use the `LSP` tool to request `hover` on the file and line from C2's result. If C2 did not return a location, use the file and line from C1's error output directly.

- **Structural**: Response has `contents` field.
- **Cross-validation**: Does hover info relate to the type/action from C1's error? The hover should describe the same symbol that verification flagged.
- **Record**: Hover content.
- If hover content returned: **PASS**. Otherwise: **FAIL** — "Hover returned empty at error location."

#### C4: Find references for error symbol

**Skip if C1 succeeded.**

Use the `LSP` tool to request `findReferences` at the same position used for C3.

- **Structural**: Returns results (at least 1 reference).
- **Reflection**: How widely is the failing symbol used? A widely-used symbol with a verification error has a larger blast radius.
- **Record**: Reference count and file list.
- If references returned: **PASS**. Otherwise: **FAIL** — "findReferences returned no results for error symbol."

#### C5: Impact analysis for error symbol

**Skip if C1 succeeded.**

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `impact`
- `symbol_name`: The symbol from C1's error output.

- **Structural**: Non-empty impact result with edges.
- **Cross-validation**: C4 returns lexical references (all occurrences), C5 returns dependency edges (modules). These are different quantities — C5 edges will typically be fewer than C4 references. Check that both are non-empty and that C5 files are a subset of C4 files.
- **Record**: Incoming/outgoing edge counts.
- If non-empty impact result: **PASS**. Otherwise: **FAIL** — "Impact analysis returned empty for error symbol."

---

### Scenario D: Edit-Verify Loop — "I'm adding a monitor" (4 checks + 2 actions)

**Skip entirely if `mode=fast` or `error-injection=false`.**

Simulates editing a spec file and verifying the change. Uses git-safe mutation.

D3 and D5 are mutation/restore **actions**, not checks — they do not produce PASS/FAIL.
If D3 fails to apply, D4-D6 are SKIPPED. If D5 fails, report FAIL with remediation instructions.

#### D1: Lint baseline (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count = 0` (file must be clean to proceed).
- **Reflection**: Baseline lint — the file must be clean before we can test mutation detection.
- **Record**: diagnostic_count value.
- If `diagnostic_count = 0`: **PASS**. If not clean: **FAIL** — skip D2-D6 (cannot run mutation on dirty file).

#### D2: Diagnostics baseline (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: Returns layered result with layer names.
- **Cross-validation**: Consistent with D1 — both should report the file as clean.
- **Record**: Layer names and summary.
- If valid layered result: **PASS**. Otherwise: **FAIL** — "Diagnostics returned no layered result."

#### D3: [ACTION] Mutate file

This is an action, not a check. It does not produce PASS/FAIL.

1. Run via Bash: `git stash push -m "nct-validate-mutation-$(date +%s)" -- <absolute-path-to-quic_types.ivy>`
2. Record the stash ref from the output (e.g., `stash@{0}`).
3. Use the `Edit` tool to insert `include nonexistent_module_xyzzy` as a new line after line 1 (`#lang ivy1.7`).
4. If the Edit fails: SKIP D4-D6.

#### D4: Lint detects mutation

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count > 0` (lint detected the injected error).
- **Reflection**: Is the error message actionable? Does it name the bad include (`nonexistent_module_xyzzy`)?
- **Record**: diagnostic_count and error message.
- If `diagnostic_count > 0`: **PASS**. If `diagnostic_count = 0`: **FAIL** — "Lint did not detect bad include."

#### D5: [ACTION] Restore file

This is an action, not a check. It does not produce PASS/FAIL.

1. Run via Bash: `git checkout -- <absolute-path-to-quic_types.ivy>`
2. Run via Bash: `git stash drop <recorded-stash-ref>`
3. If `git checkout` fails: fall back to `git stash pop`. If both fail: report **FAIL** with "file may be corrupted — run `git diff` to check."

#### D6: Lint recovery

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count = 0` (file restored to clean state).
- **Cross-validation**: Matches D1 baseline exactly — both should report 0 diagnostics.
- **Record**: diagnostic_count value.
- If `diagnostic_count = 0`: **PASS**. Otherwise: **FAIL** — "File restoration failed — lint still shows diagnostics."

---

### Scenario E: Pre-commit Health — "Is the model ready?" (6 checks)

Simulates the checks a user would run before committing changes.

#### E1: Lint (quic_frame)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_frame.ivy`

- **Structural**: Response present with `diagnostic_count` field.
- **Reflection**: Baseline lint for a core protocol file. Record whether it is clean.
- **Record**: diagnostic_count value.
- If response present: **PASS**. Otherwise: **FAIL** — "Lint returned no result."

#### E2: Quality gate (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_quality` with:
- `mode`: `gate`
- `protocol`: `quic`
- `gate_level`: `standard`

- **Structural**: Gate result present with file count and check results.
- **Reflection**: How many files reported? Are monitors present? This tells us whether the model is healthy enough to commit.
- **Record**: File count, gate checks that passed/failed.
- If gate result returned: **PASS**. Otherwise: **FAIL** — "Quality gate returned no result."

#### E3: Pattern check (quic)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_patterns` with:
- `mode`: `check`
- `protocol`: `quic`

- **Structural**: Layers and completeness report present.
- **Reflection**: Are key layers (recovery, extensions) present? This validates the model's structural completeness.
- **Record**: Layer list and completeness status.
- If layers and completeness report present: **PASS**. Otherwise: **FAIL** — "Pattern check returned no layers."

#### E4: Compile (server test file)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile` with:
- `relative_path`: `quic/quic_tests/server_tests/quic_server_test_stream.ivy`
- `target`: `test`

- **Structural**: Compilation result returned (success or failure with a clear error message).
- **Reflection**: If compilation fails, is the error message actionable? Compilation is a heavyweight operation — note the result.
- **Record**: Success/failure status and error message if any.
- If result returned (success or clear failure): **PASS**. Otherwise: **FAIL** — "Compile returned no result or crashed."

#### E5: Visualize dependencies (test file)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_visualize` with:
- `view`: `dependencies`
- `test_file`: `quic/quic_tests/server_tests/quic_server_test_stream.ivy`

- **Structural**: Returns visualization data (non-empty).
- **Reflection**: Does the dependency structure look reasonable for a test file? It should include the test file's include closure.
- **Record**: Dependency node/edge count or summary.
- If non-empty visualization data returned: **PASS**. Otherwise: **FAIL** — "Visualize returned empty."

#### E6: Diagnostics (quic_frame)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: `quic/quic_stack/quic_frame.ivy`

- **Structural**: Returns layered diagnostics with layer names.
- **Cross-validation**: Consistent with E1 lint result on the same file — if E1 reported 0 diagnostics, E6 should also report clean. If E1 showed issues, E6's full diagnostics should include them.
- **Record**: Layer summary and issue count.
- If layered diagnostics returned: **PASS**. Otherwise: **FAIL** — "Diagnostics returned no result."

---

### Scenario F: Impact Analysis — "What breaks if I change quic_packet_type?" (5 checks)

Simulates assessing the blast radius of a type change.

#### F1: Query info (quic_packet_type)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `quic_packet_type`

- **Structural**: `found: true`; response has `kind` field.
- **Reflection**: quic_packet_type is a widely-used enumeration type. Note its file and line.
- **Record**: File, line, kind.
- If found with kind: **PASS**. Otherwise: **FAIL** — "ivy_query did not find quic_packet_type."

#### F2: Impact analysis (quic_packet_type)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `impact`
- `symbol_name`: `quic_packet_type`

- **Structural**: Non-empty impact result with incoming/outgoing edges.
- **Reflection**: How many incoming/outgoing edges? As a core type, quic_packet_type should have significant impact across the model.
- **Record**: Incoming and outgoing edge counts.
- If non-empty impact result: **PASS**. Otherwise: **FAIL** — "Impact analysis returned empty for quic_packet_type."

#### F3: Include graph (full workspace)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with no `relative_path` argument (or empty).

- **Structural**: `total_files > 0`.
- **Reflection**: This reports the workspace size. The count should be a reasonable number for a multi-protocol formal model.
- **Record**: total_files value.
- If total_files > 0: **PASS**. Otherwise: **FAIL** — "Workspace include graph returned zero files."

#### F4: Find references (quic_packet_type)

Use the `LSP` tool to request `findReferences` on the file and line from F1's result, at **character 8** (the start of the symbol name, not the `object` keyword). If F1 did not return a location, use `quic/quic_stack/quic_types.ivy` at line 127, character 8.

- **Structural**: Returns multiple references.
- **Cross-validation**: Reference count should be roughly consistent with F2 impact edge count. F4 gives lexical occurrences (likely more), F2 gives dependency edges (likely fewer). Both should be non-empty for the same symbol.
- **Record**: Reference count and file list.
- If multiple references returned: **PASS**. Otherwise: **FAIL** — "findReferences returned no results for quic_packet_type."

#### F5: Go-to-definition (quic_packet_type)

Use the `LSP` tool to request `goToDefinition` at the same position used for F4.

- **Structural**: Resolves to a file with `uri` and `range`.
- **Cross-validation**: Same file as F1 query result — both MCP (ivy_query) and LSP (goToDefinition) should agree on where quic_packet_type is defined.
- **Record**: Target file and line.
- If definition resolved: **PASS**. Otherwise: **FAIL** — "goToDefinition returned no result for quic_packet_type."

---

### Negative Tests (8 checks)

Fixture-based negative tests that validate graceful handling of edge-case inputs. No file mutations — uses bad inputs or invalid positions. These always run (not skipped in fast mode).

#### FX1: Nonexistent symbol query

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- `mode`: `info`
- `symbol_name`: `nonexistent_xyzzy_42`

- **Structural**: `found: false` or graceful empty result; no stack traces in output.
- If graceful not-found response: **PASS**. Otherwise: **FAIL** — "Ungraceful error on nonexistent symbol."

#### FX2: Coverage stats — nonexistent protocol

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `stats`
- `relative_path`: `new_prot/`

- **Structural**: `total: 0` or graceful empty result; no stack traces.
- If graceful response: **PASS**. Otherwise: **FAIL** — "Ungraceful error on empty directory."

#### FX3: Include graph — standalone file

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_include_graph` with:
- `relative_path`: `quic/quic_stack/quic_h3_error_code.ivy`

- **Structural**: Empty or very small includes list (standalone file); no crash.
- If includes list is empty or very small: **PASS**. Otherwise: **FAIL** — "Unexpected includes for standalone file."

#### FX4: Model summary — non-test file

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_summary` with:
- `test_file`: `quic/quic_stack/quic_transport_error_code.ivy`

- **Structural**: Graceful result (may be empty — non-test file has no test actions); no stack traces or crash errors.
- If graceful result (even empty): **PASS**. Otherwise: **FAIL** — "Ungraceful error on non-test file."

#### FX5: Coverage gaps — nonexistent protocol

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with:
- `mode`: `gaps`
- `protocol`: `new_prot`

- **Structural**: Empty gaps list or graceful "no requirements" response; no stack traces.
- If graceful response: **PASS**. Otherwise: **FAIL** — "Ungraceful error on nonexistent protocol."

#### FX6: LSP hover — invalid position

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line 9999, character 0.

- **Structural**: Empty hover or graceful null response; no crash or timeout.
- If graceful response (even empty): **PASS**. Otherwise: **FAIL** — "LSP crashed on invalid hover position."

#### FX7: LSP documentSymbol — nonexistent file

Use the `LSP` tool to request `documentSymbol` on `nonexistent_file_xyzzy.ivy`.

- **Structural**: Empty list or graceful error response; no crash.
- If graceful response: **PASS**. Otherwise: **FAIL** — "LSP crashed on nonexistent file."

#### FX8: LSP goToDefinition — invalid position

Use the `LSP` tool to request `goToDefinition` on `quic/quic_stack/quic_types.ivy` at line 9999, character 0.

- **Structural**: Empty result or graceful null response; no crash.
- If graceful response (even empty): **PASS**. Otherwise: **FAIL** — "LSP crashed on invalid goToDefinition position."

---

## Pass 2: Gap Sweep (~6 checks)

**Skip if `mode=fast`.**

One structural call per MCP tool or LSP operation NOT exercised in Pass 1. The gap sweep ensures no tool is completely untested.

### GS1: ivy_scope

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_scope` with no arguments (or minimal required arguments).

- **Structural**: Responds without error.
- If response received: **PASS**. Otherwise: **FAIL** — "ivy_scope returned error."

### GS2: ivy_manifest

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_manifest` with no arguments (or minimal required arguments).

- **Structural**: Responds without error.
- If response received: **PASS**. Otherwise: **FAIL** — "ivy_manifest returned error."

### GS3: ivy_pattern_scaffold

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_pattern_scaffold` with minimal required arguments (e.g., `protocol`: `quic`, `pattern`: `monitor`).

- **Structural**: Responds without error.
- If response received: **PASS**. Otherwise: **FAIL** — "ivy_pattern_scaffold returned error."

### GS4: ivy_verification_dashboard

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verification_dashboard` with no arguments (or minimal required arguments).

- **Structural**: Responds without error.
- If response received: **PASS**. Otherwise: **FAIL** — "ivy_verification_dashboard returned error."

### GS5: LSP callHierarchy

Use the `LSP` tool to request `prepareCallHierarchy` on `quic/quic_stack/quic_types.ivy` at line 1, character 0.

- **Structural**: Responds without error (may return empty — this is a documented limitation).
- If response received (even empty): **PASS**. Otherwise: **FAIL** — "LSP callHierarchy crashed."

### GS6: LSP goToImplementation

Use the `LSP` tool to request `goToImplementation` on `quic/quic_stack/quic_types.ivy` at line 1, character 0.

- **Structural**: Responds without error (may return empty).
- If response received (even empty): **PASS**. Otherwise: **FAIL** — "LSP goToImplementation crashed."

### Tool Coverage Matrix

After the gap sweep (or after Pass 1 if gap sweep is skipped), present this matrix showing which tools were exercised:

```markdown
| Tool                         | Scenario | Gap Sweep | Status   |
|------------------------------|----------|-----------|----------|
| ivy_lint                     | D, E     |           | covered  |
| ivy_verify                   | C        |           | covered  |
| ivy_compile                  | E        |           | covered  |
| ivy_model_info               | A        |           | covered  |
| ivy_diagnostics              | D, E     |           | covered  |
| ivy_query(info)              | A, B, C, F |         | covered  |
| ivy_query(impact)            | C, F     |           | covered  |
| ivy_coverage(stats)          | B        |           | covered  |
| ivy_coverage(gaps)           | B        |           | covered  |
| ivy_coverage(matrix)         | B        |           | covered  |
| ivy_extract_requirements     | B        |           | covered  |
| ivy_include_graph            | A, F     |           | covered  |
| ivy_visualize                | E        |           | covered  |
| ivy_model_summary            | B        |           | covered  |
| ivy_quality                  | E        |           | covered  |
| ivy_patterns                 | E        |           | covered  |
| ivy_capabilities             | (P0)     |           | covered  |
| ivy_scope                    |          | GS1       | covered  |
| ivy_manifest                 |          | GS2       | covered  |
| ivy_pattern_scaffold         |          | GS3       | covered  |
| ivy_verification_dashboard   |          | GS4       | covered  |
| LSP hover                    | A, C     |           | covered  |
| LSP documentSymbol           | A        |           | covered  |
| LSP goToDefinition           | A, F     |           | covered  |
| LSP findReferences           | A, C, F  |           | covered  |
| LSP workspaceSymbol          | A        |           | covered  |
| LSP goToImplementation       |          | GS6       | covered  |
| LSP callHierarchy            |          | GS5       | covered  |
```

---

## Pass 3: Non-Workflow Checks (23 checks)

### Hooks (14 checks)

Read `hooks/hooks.json` (relative to the plugin root `${CLAUDE_PLUGIN_ROOT}`) using the `Read` tool. Use the contents to validate each hook registration below.

#### H1: SessionStart hook fired (detect-ivy-workspace)

Read the beginning of this session's system-reminder messages (already in your context) and look for the `[ivy-workspace] Detected PANTHER project` message.

- **Structural**: The message is present in the session context.
- If message found: **PASS** — quote the message.
- If not found: **FAIL** — "SessionStart hook did not fire or workspace not detected."

#### H2: SessionStart hook registered (obs_session_start.py)

Verify that `hooks.json` contains a `SessionStart` section with a command containing `obs_session_start.py`.

- **Structural**: Hook entry exists under `SessionStart` with script path `obs_session_start.py`.
- If found: **PASS** — report the hook entry.
- If not found: **FAIL** — "obs_session_start.py not registered in SessionStart hooks."

#### H3: PreToolUse hook registered (block-direct-ivy)

Verify that `hooks.json` contains a `PreToolUse` hook with matcher `"Bash"` and command containing `block-direct-ivy.sh`.

- **Structural**: Hook entry exists with matcher `Bash` and script path `block-direct-ivy.sh`.
- If found: **PASS**. If not found: **FAIL** — "block-direct-ivy hook not registered."

#### H4: PreToolUse hook registered (lint-before-verify)

Verify that `hooks.json` contains a `PreToolUse` hook with matcher `"ivy_verify"` and command containing `lint-before-verify.sh`.

- **Structural**: Hook entry exists with matcher `ivy_verify` and script path `lint-before-verify.sh`.
- If found: **PASS**. If not found: **FAIL** — "lint-before-verify hook not registered."

#### H5: PreToolUse hook registered (check_lsp_log.py)

Verify that `hooks.json` contains a `PreToolUse` hook with matcher `"mcp__.*ivy"` and command containing `check_lsp_log.py`.

- **Structural**: Hook entry exists with matcher `mcp__.*ivy` and script path `check_lsp_log.py`.
- **Reflection**: This hook monitors LSP health before MCP tool calls. It was previously unvalidated (BUG-1 fix).
- If found: **PASS**. If not found: **FAIL** — "check_lsp_log.py hook not registered."

#### H6: PreToolUse hook registered (observability — global)

Verify that `hooks.json` contains a `PreToolUse` hook with empty matcher `""` and command containing `obs_pre_tool_use.py`.

- **Structural**: Hook entry exists with empty matcher and script path `obs_pre_tool_use.py`.
- If found: **PASS**. If not found: **FAIL** — "PreToolUse observability hook not registered."

#### H7: PostToolUse hook registered (post-write-ivy-lint)

Verify that `hooks.json` contains a `PostToolUse` hook with matcher `"Write|Edit"` and command containing `post-write-ivy-lint.sh`.

- **Structural**: Hook entry exists with matcher `Write|Edit` and script path `post-write-ivy-lint.sh`.
- If found: **PASS**. If not found: **FAIL** — "post-write-ivy-lint hook not registered."

#### H8: PostToolUse hook registered (observability — global)

Verify that `hooks.json` contains a `PostToolUse` hook with empty matcher `""` and command containing `obs_post_tool_use.py`.

- **Structural**: Hook entry exists with empty matcher and script path `obs_post_tool_use.py`.
- If found: **PASS**. If not found: **FAIL** — "PostToolUse observability hook not registered."

#### H9: PostToolUseFailure hook registered

Verify that `hooks.json` contains a `PostToolUseFailure` section with command containing `obs_post_tool_use_failure.py`.

- **Structural**: Hook entry exists with script path `obs_post_tool_use_failure.py`.
- If found: **PASS**. If not found: **FAIL** — "PostToolUseFailure hook not registered."

#### H10: SessionEnd hook registered

Verify that `hooks.json` contains a `SessionEnd` section with command containing `obs_session_end.py`.

- **Structural**: Hook entry exists with script path `obs_session_end.py`.
- If found: **PASS**. If not found: **FAIL** — "SessionEnd hook not registered."

#### H11: Stop hooks registered (both scripts)

Verify that `hooks.json` contains a `Stop` section with **both**:
- A command containing `stop-session-summary.sh`
- A command containing `obs_stop.py`

- **Structural**: Both stop hook entries exist.
- If both found: **PASS**. If either missing: **FAIL** — report which is missing.

#### H12: SubagentStart + SubagentStop hooks registered

Verify that `hooks.json` contains both:
- A `SubagentStart` section with command containing `obs_subagent_start.py`
- A `SubagentStop` section with command containing `obs_subagent_stop.py`

- **Structural**: Both hook entries exist.
- If both found: **PASS**. If either missing: **FAIL** — report which is missing.

#### H13: Remaining observability hooks registered

Verify that `hooks.json` contains all four:
- `PreCompact` with `obs_pre_compact.py`
- `UserPromptSubmit` with `obs_user_prompt_submit.py`
- `Notification` with `obs_notification.py`
- `PermissionRequest` with `obs_permission_request.py`

- **Structural**: All four hook entries exist.
- If all four found: **PASS**. If any missing: **FAIL** — report which are missing.

#### H14: All hook scripts exist and are readable

For every script referenced in `hooks.json`, use the `Read` tool to read the first line of each script file (resolved relative to plugin root). Verify each has a shebang (`#!/`) or Python import/comment as first line.

Scripts to check (from `hooks/scripts/`):
- `block-direct-ivy.sh`
- `lint-before-verify.sh`
- `check-indexing-ready.sh`
- `post-write-ivy-lint.sh`
- `detect-ivy-workspace.sh`
- `wait-for-indexing.sh`
- `stop-session-summary.sh`
- `cleanup-ivy-lsp.sh`
- `interaction-checkpoint.py`
- `observability/check_lsp_log.py`
- `observability/obs_pre_tool_use.py`
- `observability/obs_post_tool_use.py`
- `observability/obs_post_tool_use_failure.py`
- `observability/obs_session_start.py`
- `observability/obs_session_end.py`
- `observability/obs_stop.py`
- `observability/obs_subagent_start.py`
- `observability/obs_subagent_stop.py`
- `observability/obs_pre_compact.py`
- `observability/obs_user_prompt_submit.py`
- `observability/obs_notification.py`
- `observability/obs_permission_request.py`

- **Structural**: All scripts exist and have a valid first line.
- If all scripts exist and are readable: **PASS** — report count.
- If any missing: **FAIL** — report which scripts are missing.

---

### Surface (4 checks)

#### S1: Commands count

Use `Glob` to find `commands/*.md` relative to the plugin root (excluding `README.md`). For each file, verify YAML frontmatter contains `name` and `description` fields.

- **Structural**: At least 1 command file found with valid frontmatter.
- **Record**: Actual count and list of command names.
- If commands found with valid frontmatter: **PASS** — report count. Otherwise: **FAIL** — report issues.

#### S2: Skills count

Use `Glob` to find `skills/*/SKILL.md` relative to the plugin root. For each file, verify YAML frontmatter contains `name` and `description` fields.

- **Structural**: At least 1 skill file found with valid frontmatter.
- **Record**: Actual count and list of skill names.
- If skills found with valid frontmatter: **PASS** — report count. Otherwise: **FAIL** — report issues.

#### S3: MCP tools count

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` and count the reported tools.

- **Structural**: Count > 0.
- **Record**: Actual count for interactive review.
- If count > 0: **PASS** — report actual count. Otherwise: **FAIL** — "No MCP tools reported."

#### S4: Observability log validation

Check for observability log files. Use Bash to check for files matching `~/.claude/ivy-observability/*.jsonl` or `$TMPDIR/ivy-obs-*.jsonl`.

If log files found, validate:
1. File is valid JSONL (each line is parseable JSON).
2. At least one `SessionStart` event is present.

- If valid JSONL with at least 1 SessionStart event: **PASS**.
- If log directory exists but no SessionStart event: **PASS (partial)** — "Logs exist but no SessionStart (may be fresh session)."
- If no log directory or no files: **SKIPPED** — "No observability logs found (fresh session)."

---

### Agents (5 checks)

**Skip if `mode=fast`.**

Each agent is dispatched sequentially. Validation is structural (response length, no stack traces) plus cross-validation against earlier scenario results.

Timeout: 120s per agent. Mark SKIPPED on timeout or if agent dispatch fails.

#### AG1: spec-analyst (exploration)

Dispatch `panther-ivy-plugin:spec-analyst` with prompt:
> "List all types defined in quic_types.ivy with their line numbers."

- **Structural**: Response > 50 chars, no stack traces.
- **Cross-validation**: Response mentions type names seen in Scenario A (A1 model_info, A2 documentSymbol). Do the types listed by the agent overlap with what A1 and A2 reported?
- If valid response with type names: **PASS** — report response length and matched types. Otherwise: **FAIL**.

#### AG2: spec-analyst (verification)

Dispatch `panther-ivy-plugin:spec-analyst` with prompt:
> "Run ivy_verify on quic_types.ivy and explain the failure."

- **Structural**: Response > 50 chars, no stack traces.
- **Cross-validation**: Response mentions the same error context as Scenario C (C1 verify result). Does the agent identify the same failing symbol?
- If valid response referencing verification: **PASS**. Otherwise: **FAIL**.

#### AG3: methodology-guide (NCT)

Dispatch `panther-ivy-plugin:methodology-guide` with prompt:
> "I have an uncovered MUST requirement from RFC 9000. What NCT step should I follow to add a monitor?"

- **Structural**: Response > 100 chars, coherent advice, no stack traces.
- **Reflection**: Does the response reference NCT workflow steps? Is the advice actionable?
- If valid response with methodology guidance: **PASS**. Otherwise: **FAIL**.

#### AG4: model-reviewer (review)

Dispatch `panther-ivy-plugin:model-reviewer` with prompt:
> "Review quic_types.ivy for specification quality issues."

- **Structural**: Response identifies at least 1 concrete observation, references file content, no stack traces.
- **Reflection**: Does the review provide actionable feedback about the specification?
- If valid response with concrete observations: **PASS**. Otherwise: **FAIL**.

#### AG5: traceability-agent (coverage)

Dispatch `panther-ivy-plugin:traceability-agent` with prompt:
> "What is the RFC 9000 coverage breakdown for QUIC?"

- **Structural**: Response > 50 chars, mentions requirement categories (MUST, SHOULD, MAY, etc.), no stack traces.
- **Cross-validation**: Coverage numbers roughly consistent with Scenario B (B1 coverage stats). Do the totals or breakdowns align?
- If valid response with coverage data: **PASS**. Otherwise: **FAIL**.

---

## Pass 4: Interactive Review

After all automated checks complete, present a consolidated table of all recorded values. Group by scenario for readability.

**In `mode=fast`**: Print the table directly without waiting for user confirmation.

```markdown
# Interactive Review

## Scenario A: Exploration
| # | Check | Value |
|---|-------|-------|
| 1 | A1: model_info types | {list of types from A1} |
| 2 | A2: documentSymbol count | {count} symbols |
| 3 | A3: hover on cid | {hover content summary} |
| 4 | A5: findReferences cid | {count} references across {files} files |
| 5 | A7: include_graph count | {count} modules |
| 6 | A8: cid location | {file}:{line} |

## Scenario B: Coverage
| # | Check | Value |
|---|-------|-------|
| 7 | B1: total requirements | {total} (MUST:{n}, MUST_NOT:{n}, SHOULD:{n}, SHOULD_NOT:{n}, MAY:{n}) |
| 8 | B2: uncovered gaps | {count} uncovered requirements |
| 9 | B4: matrix covered | {count} requirements mapped |
| 10| B6: action count | {count} actions |

## Scenario C: Debug
| # | Check | Value |
|---|-------|-------|
| 11| C1: verify result | {PASS/FAIL on symbol (line)} |
| 12| C5: impact edges | {incoming} incoming, {outgoing} outgoing |

## Scenario D: Edit-Verify (if run)
| # | Check | Value |
|---|-------|-------|
| 13| D1: lint baseline | {diagnostic_count} diagnostics |
| 14| D4: lint after mutation | {diagnostic_count} diagnostics |
| 15| D6: lint after recovery | {diagnostic_count} diagnostics |

## Scenario E: Pre-commit
| # | Check | Value |
|---|-------|-------|
| 16| E1: lint quic_frame | {diagnostic_count} diagnostics |
| 17| E2: quality gate | {gate result summary} |
| 18| E4: compile result | {success/failure} |

## Scenario F: Impact
| # | Check | Value |
|---|-------|-------|
| 19| F1: quic_packet_type info | {kind} in {file} |
| 20| F2: impact edges | {incoming} incoming, {outgoing} outgoing |
| 21| F3: workspace total files | {total_files} |

## Cross-Validation Summary
| Pair | Agreement |
|------|-----------|
| A3+A4+A6+A8 cid location | {agree/disagree}: {details} |
| D1+D6 lint baseline/recovery | {agree/disagree}: {details} |
| B1 total vs level sum | {total} = {sum breakdown} |
| C4 refs vs C5 impact | {agreement details} |
| E1+E6 lint vs diagnostics | {agree/disagree}: {details} |
| F1+F5 definition location | {agree/disagree}: {details} |
| F2+F4 impact vs references | {agree/disagree}: {details} |
| D1+D2 lint vs diagnostics | {agree/disagree}: {details} |
| A1+A2 model_info vs documentSymbol | {agree/disagree}: {details} |

Reply with row numbers to REJECT, or "all good" to confirm all values.
```

---

## SR1: Self-Review

Run this after all other passes complete. Analyze the complete set of results:

### 1. Completeness

Every check produced PASS, FAIL, or SKIPPED (no undefined status). Count any missing results.

### 2. Cross-Validation Consistency

Evaluate each of the 9 defined cross-validation pairs. Flag any that disagreed.

| Pair | What must agree |
|------|-----------------|
| A1 (model_info) + A2 (documentSymbol) | Type names overlap |
| A3 (hover cid) + A4 (goToDefinition cid) + A6 (workspaceSymbol cid) + A8 (ivy_query cid) | All locate cid in same file |
| D1 (lint baseline) + D6 (lint recovery) | Both report 0 diagnostics |
| D1 (lint) + D2 (diagnostics) | Both report clean on same file |
| E1 (lint) + E6 (diagnostics) | Both report clean on same file |
| B1 (coverage total) + B1 (level sum) | total = MUST + MUST_NOT + SHOULD + SHOULD_NOT + MAY |
| C4 (findReferences) + C5 (impact) | Both non-empty, C5 files subset of C4 files |
| F1 (query info) + F5 (goToDefinition) | Same file for quic_packet_type |
| F2 (impact) + F4 (findReferences) | Both non-empty for quic_packet_type |

Compute: `cross_validation_agreement = pairs_that_agree / total_pairs_evaluated` (pairs where one side is SKIPPED are excluded from the denominator).

### 3. Reflection Quality

All reflections are present and non-empty. Every check has a 1-2 sentence reflection.

### 4. Tool Coverage

Present the tool coverage matrix (from Pass 2 section). Flag any tools that were never called.

### 5. Score

Calculate the quality score:

```
score = 100 * (pass_rate * 0.7 + cross_validation_agreement * 0.3)
```

Where:
- `pass_rate = passed / (passed + failed)` — excludes SKIPPED
- `cross_validation_agreement = pairs_that_agree / total_pairs_evaluated`

- If all sub-checks pass (completeness, consistency, reflections, coverage): **PASS** with score.
- If any issue found: **FAIL** — report each issue.

---

## Result Presentation Format

Present the final results in this format:

```markdown
# Ivy Integration Validation Report (v3)

**Date**: {timestamp}
**Workspace**: {detected workspace root}
**Command**: `/nct-validate {args}`
**Mode**: full / fast
**Passes run**: {list}

## Summary

| Pass | Name | Checks | Passed | Failed | Skipped |
|------|------|--------|--------|--------|---------|
| 0 | Pre-flight | 3 | ? | ? | ? |
| 1 | Scenarios + Negatives | 42 | ? | ? | ? |
|   | - A: Exploration | 8 | ? | ? | ? |
|   | - B: Coverage | 6 | ? | ? | ? |
|   | - C: Debug | 5 | ? | ? | ? |
|   | - D: Edit-Verify | 4 (+2 actions) | ? | ? | ? |
|   | - E: Pre-commit | 6 | ? | ? | ? |
|   | - F: Impact | 5 | ? | ? | ? |
|   | - Negative tests | 8 | ? | ? | ? |
| 2 | Gap Sweep | ~6 | ? | ? | ? |
| 3 | Non-workflow | 23 | ? | ? | ? |
|   | - Hooks | 14 | ? | ? | ? |
|   | - Surface | 4 | ? | ? | ? |
|   | - Agents | 5 | ? | ? | ? |
| 4 | Interactive | - | - | - | - |
| SR | Self-Review | 1 | ? | ? | ? |
| **Total** | | **~75** | **?** | **?** | **?** |

**Quality Score**: NN/100
```

### Per-check detail format

For each check, report:

```markdown
### {ID}: {Title}
- **Tool**: {tool name and params}
- **Status**: PASS / FAIL / SKIPPED
- **Value**: {actual value returned}
- **Reflection**: {1-2 sentences connecting to prior results}
- **Cross-validation**: {if applicable, comparison with prior check}
```

---

## Suggested Actions

If any checks fail, include a `### Suggested Actions` section at the end of the report:

- If P1 fails: "Start the Ivy LSP server. Check if `ivy_lsp` is installed and in PATH."
- If P2 fails: "The MCP server is not reachable. Check plugin configuration and `/tmp/ivy-lsp-latest.log`."
- If P3 fails: "LSP is running but not responding to requests. Check workspace indexing in `/tmp/ivy-lsp-latest.log`."
- If any Scenario A-F check fails: "MCP or LSP tool returned unexpected results. Check `/tmp/ivy-lsp-latest.log` for errors. Verify the workspace is fully indexed."
- If any D-check fails (mutation): "Mutation test failed. Check that `ivy_lint` properly detects the mutation type. Verify file was restored cleanly with `git diff`."
- If any FX check fails: "Negative test failed — tool did not handle edge-case input gracefully. Check tool error handling in the MCP server. See `/tmp/ivy-mcp-latest.log`."
- If any H-check fails: "Hook not registered or script missing. Check `hooks/hooks.json` for the expected event type and script path. Verify scripts exist in `hooks/scripts/`."
- If any AG-check fails: "Agent did not respond as expected. Verify agent definition in `agents/` directory. Check that the agent's tools are available."
- If any S-check fails: "Surface coverage gap detected. Verify command/skill files exist with proper YAML frontmatter."
- If SR1 fails: "Self-review found issues. Address the specific sub-check failures listed in the SR1 details."
- If `protocol-testing/` directory is missing: "Protocol models not found. Run `git submodule update --init` from the panther_ivy directory."

See the `tooling-reference` skill for tool architecture.
