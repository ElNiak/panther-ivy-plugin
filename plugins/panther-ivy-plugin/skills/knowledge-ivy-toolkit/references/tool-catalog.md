# Ivy-Tools MCP Tool Catalog

Standardized per-tool reference. Timeout, Tier, and Rendering values come from
`_TOOL_TIMEOUTS` and `_TOOL_METADATA` in `ivy_lsp/mcp/tools/__init__.py`.

**Rendering note:** Tools marked `hook` are post-processed by `render-tool-result.py`.
Do not reformat their output. Tools marked `raw` return JSON — format per ivy-formatting.md.

---

## 1. Verification and Compilation

### ivy_verify
Run `ivy_check` on an Ivy file to verify formal properties.

| Field | Value |
|-------|-------|
| Parameters | relative_path (str), isolate (str, None), use_cache (bool, False), compact (bool, True), scope (str, ""), timeout (float, 120.0) |
| Returns | { success, diagnostics, diagnostic_count, duration_seconds, counterexample_trace?, cached } |
| Timeout | 600s |
| Tier | blocking |
| Rendering | hook |
| Concurrency | shares compilation semaphore; in-flight dedup prevents parallel runs for same (file, isolate) |

**Errors:**
- `"ivy_check CLI not found on PATH"` → Ivy not installed; run inside Docker or install natively
- `"File not found: <path>"` → relative_path doesn't exist; check workspace root
- `"Model timed out after <N>s"` → model too complex; increase timeout param or use isolate= to narrow scope
- `"Tool queued too long (>Ns)"` → concurrency slot unavailable; other blocking tools running; wait and retry

**When to use:** Final formal property verification; use `ivy_diagnostics(mode="structural")` first during edit loops.

---

### ivy_compile
Compile an Ivy file to a test executable using `ivyc`.

| Field | Value |
|-------|-------|
| Parameters | relative_path (str), target (str, "test"), isolate (str, None), scope (str, "") |
| Returns | { success, diagnostics, diagnostic_count, error_summary, raw_output, duration_seconds } |
| Timeout | 360s |
| Tier | blocking |
| Rendering | hook |
| Concurrency | shares compilation semaphore with ivy_verify |

**Errors:**
- `"ivyc CLI not found on PATH and no Docker image configured"` → needs Docker executor or native ivyc
- `"Docker setup failed (exit N)"` → container setup error; check Docker daemon and image availability
- `"File not found: <path>"` → relative_path doesn't exist; verify path relative to workspace root
- `"Invalid parameter"` → isolate or target contains shell-unsafe characters

**When to use:** Generate the test binary for IUT testing; required before `ivy_iut_test`.

---

### ivy_model_info
Display the structure of an Ivy model using `ivy_show`.

| Field | Value |
|-------|-------|
| Parameters | relative_path (str), isolate (str, None) |
| Returns | { success, output, duration_seconds, redirected_from?, redirected_to? } |
| Timeout | 60s |
| Tier | fast |
| Rendering | raw |
| Concurrency | standard |

**Errors:**
- `"ivy_show CLI not found on PATH"` → Ivy not installed; only available inside Docker
- `"File not found: <path>"` → path doesn't exist
- Auto-redirects to test entry point when no isolate is specified; `redirected_to` shows effective path

**When to use:** Inspect types, relations, and actions in a model without full verification.

---

## 2. Analysis and Diagnostics

### ivy_diagnostics
Multi-layer diagnostic analysis of an Ivy file, plus workspace-level verification dashboard.

| Field | Value |
|-------|-------|
| Parameters (structural/full/collisions) | relative_path (str), mode (str, "full"), layers (list[str], None), min_severity (str, None), scope (str, "") |
| Parameters (dashboard) | mode="dashboard" |
| Returns (structural/full/collisions) | { diagnostics, diagnostic_count, by_source, error_count, warning_count } |
| Returns (dashboard) | { success, total_files, verified, failed, pending, cache_size, cache_max, verified_files, failed_files } |
| Timeout | 120s |
| Tier | fast (structural mode), slow (full/dashboard modes) |
| Rendering | hook |
| Concurrency | needs_model=True; waits for model build before full/semantic layers |

**Errors:**
- `"Unknown mode '<m>'"` → valid modes: structural, full, collisions, dashboard
- `"Model is still building"` → model not ready; use mode="structural" or retry in 30s
- `"File not found: <path>"` → path doesn't exist
- Empty `verified_files` and `failed_files` (dashboard) → cache is cold; no verifications have been run yet
- `cache_size == 0` (dashboard) after running `ivy_verify` → verify that `use_cache=True` was set on the call

**When to use:** `mode="structural"` after every file edit (instant); `mode="full"` before committing changes; `mode="collisions"` to debug include resolution conflicts; `mode="dashboard"` for workspace-level verification overview before a review session.

---

### ivy_analysis
Consolidated analysis tool: include dependency graph (mode="includes") or endpoint mirror scope (mode="scope").

| Field | Value |
|-------|-------|
| Parameters (mode="includes") | relative_path (str, None), detail (str, "summary"), limit (int, 30), scope (str, "") |
| Parameters (mode="scope") | relative_path (str) |
| Returns (includes, focused) | { file, includes, included_by, transitive_includes } |
| Returns (includes, summary) | { total_files, entry_points, entry_point_count, most_included } |
| Returns (scope) | { file, endpoint_mirrors, endpoint_mirror_count, tester_role?, include_closure?, include_closure_size?, exported_actions?, imported_actions?, partition?, collision_report? } |
| Timeout | 60s |
| Tier | slow (includes) / fast (scope) |
| Rendering | raw |
| Concurrency | standard (includes) / needs_model=True (scope) |

**Errors:**
- `"Skipping unreadable file"` (warning, includes mode) → OSError reading a file; graph is partial
- Ambiguous resolution (includes mode): `includes[].candidates` lists all matching files when basename is not unique
- `"File not found: <path>"` (scope mode) → path doesn't exist
- `"Model is still building"` (scope mode) → retry in 30s
- Empty `endpoint_mirrors` (scope mode) → file is not a test entry point; check include graph

**When to use:** `mode="includes"` to understand include chains, find entry points, or diagnose unresolved includes. `mode="scope"` to determine the tester role and include closure for a test file before running coverage or verification.

---

### ivy_status
Consolidated status tool: CLI tool availability (mode="capabilities") or server health (mode="health").

| Field | Value |
|-------|-------|
| Parameters | mode (str: capabilities/health) |
| Returns (capabilities) | { success, cli_tools, mcp_tools, mcp_tool_count, workspace_index_loaded, parsing_tiers, staging_health } |
| Returns (health) | { success, server, model_status, verification_cache, tool_metrics, capabilities, workspace_files } |
| Timeout | 10s |
| Tier | instant |
| Rendering | raw |
| Concurrency | local_only; never delegated to sidecar |

**Errors:**
- `"parsing_tiers": {"error": "probe timed out"}` (capabilities) → parser tier detection exceeded 3s; non-fatal
- `"workspace_index_loaded": false` (capabilities) → index not yet built; call `ivy_index` to build
- `"verification_cache": {"error": "<exc>"}` (health) → cache summary failed; non-fatal, server still running
- `"workspace_files": -1` (health) → find_ivy_files threw; check workspace root path

**When to use:** First step in any triage sequence; `mode="capabilities"` to confirm MCP connectivity and CLI tool availability; `mode="health"` to inspect uptime, cache status, tool metrics, and model status.

---

## 3. Coverage and Traceability

### ivy_coverage
Unified RFC requirement coverage analysis.

| Field | Value |
|-------|-------|
| Parameters | mode (str, "stats"), relative_path (str, None), test_file (str, None), protocol (str, None), compact (bool, True), max_items (int, 50), scope (str, "") |
| Returns (stats) | { total, covered, uncovered, coverage_percent, by_level, by_layer, uncovered_ids } |
| Returns (matrix) | { total_requirements, covered, uncovered, matrix } |
| Returns (gaps) | { unguardedStateVars, uncoveredRfcRequirements, orphanRequirements, summary } |
| Returns (diff) | { baseline_coverage_percent, current_coverage_percent, delta_percent, new_gaps, recovered } |
| Timeout | 120s |
| Tier | slow |
| Rendering | hook |
| Concurrency | needs_model=True |

**Errors:**
- `"Unknown mode '<m>'"` → valid: matrix, stats, gaps, diff
- `"Model is still building"` → retry in 30s
- `"No coverage baseline cached"` (diff mode) → run `mode="stats"` first to create baseline
- `"No requirements found"` → no manifest loaded; run `ivy_manifest(mode="info")` to check

**When to use:** `mode="stats"` for overall coverage; `mode="gaps"` to find unguarded state; `mode="matrix"` for full requirement-to-assertion mapping; `mode="diff"` after edits to see regression.

---

### ivy_extract_requirements
Parse RFC text to extract MUST/SHOULD/MAY normative requirements.

| Field | Value |
|-------|-------|
| Parameters | rfc_text (str, ""), output (str, "structured"), rfc_name (str, ""), protocol (str, ""), base_section (str, ""), rfc_source (str, ""), sections (str, "") |
| Returns (structured) | { requirements, total, by_level } |
| Returns (manifest) | { yaml, total_requirements, suggested_path, by_level } |
| Timeout | 30s |
| Tier | slow |
| Rendering | raw |
| Concurrency | standard |

**Errors:**
- `"Either rfc_text or rfc_source must be provided"` → pass at least one text source
- `"rfc_name is required for output='manifest'"` → add rfc_name parameter
- `"Failed to fetch RFC: <exc>"` → network error fetching rfc_source; check connectivity or use rfc_text

**When to use:** Generate a requirements manifest from raw RFC text as the first step in traceability setup.

---

### ivy_manifest
Discover, validate, and manage requirement manifest files.

| Field | Value |
|-------|-------|
| Parameters | mode (str, "info"), protocol (str, ""), rfc_source (str, ""), check_online (bool, False) |
| Returns (info) | { manifests, total_manifests, protocols_without_manifests } |
| Returns (validate) | { results, total_manifests, all_valid } |
| Returns (staleness) | { reports } |
| Returns (refresh) | { rfc_source, new_requirements_found, current_manifest_ids, by_level } |
| Timeout | 60s |
| Tier | fast |
| Rendering | raw |
| Concurrency | standard |

**Errors:**
- `"Unknown mode '<m>'"` → valid: info, validate, staleness, refresh
- `"rfc_source is required for mode='refresh'"` → provide an RFC number or URL
- `"Failed to fetch/parse: <exc>"` → network or parse error in refresh mode

**When to use:** Audit manifest completeness before running coverage; `mode="validate"` to catch malformed manifests.

---

## 4. RFC Lookup

### ivy_rfc
Retrieve, search, and analyze RFC documents.

| Field | Value |
|-------|-------|
| Parameters | mode ("get"\|"search"\|"section"), number (str, None), query (str, None), format (str, "full"), section (str, None), analyze (bool, True), limit (int, 10) |
| Returns (get) | { status, number, title, format, sections? } |
| Returns (search) | { status, query, count, results: [{ number, title, date, status, abstract }] } |
| Returns (section) | { status, rfc, section, title, text, normative_statements?, cross_references? } |
| Timeout | 30s |
| Tier | fast |
| Rendering | raw |
| Concurrency | local_only; no sidecar delegation |

**Errors:**
- `"RFC service not initialized."` → server startup failed; check `ivy_status(mode="health")`
- `"'number' is required for mode='get'."` → missing required parameter
- `"Failed to fetch RFC <N>"` → network error or invalid RFC number; check IVY_LSP_RFC_OFFLINE
- `"Section <s> not found in RFC <N>."` → section doesn't exist; use mode="get" with format="sections" to list

**When to use:** `mode="search"` to find RFCs, `mode="get"` for TOC/full text, `mode="section"` with `analyze=True` for normative MUST/SHOULD/MAY extraction with bracket-tag-compatible IDs.

---

## 5. Visualization

### ivy_visualize
Unified model visualization with five views.

| Field | Value |
|-------|-------|
| Parameters | view (str, "dependencies"), test_file (str, None), protocol (str, None), include_state_vars (bool, False), state_var_filter (str, None), group_by (str, "file"), max_items (int, 50), sort_by (str, None), limit (int, None), action_name (str, None), file_path (str, None), offset (int, 0) |
| Returns (dependencies) | { nodes, edges, total_actions } |
| Returns (state_machine) | { states, transitions, total_states } |
| Returns (layers) | { layers, total_files } |
| Returns (summary) | { rows, total_actions } |
| Returns (requirements) | { actions, total_actions } |
| Timeout | 60s |
| Tier | fast |
| Rendering | raw |
| Concurrency | needs_model=True |

**Errors:**
- `"Unknown view '<v>'"` → valid: dependencies, state_machine, layers, summary, requirements
- `"Model is still building"` → retry in 30s
- Empty nodes/states/rows → model has no actions or index not built; check that test_file or protocol resolves correctly; run `ivy_index` first if empty

**When to use:** `view="dependencies"`/`"state_machine"`/`"layers"` to understand action chains, state relationships, and architecture before modifying behavior layers. `view="summary"` to list per-action statistics. `view="requirements"` to inspect before/after monitors for a specific action.

---

## 6. Quality and Patterns

### ivy_quality
Context-aware suggestions and quality gate validation.

| Field | Value |
|-------|-------|
| Parameters | mode (str, "suggestions"), file_path (str, None), line (int, None), context (str, None), protocol (str, None), gate_level (str, "minimal"), max_items (int, 50) |
| Returns (suggestions) | { suggestions, total } |
| Returns (gate) | { protocol, gate_level, passed, checks_passed, checks_total, checks } |
| Timeout | 60s |
| Tier | slow |
| Rendering | hook |
| Concurrency | needs_model=True |

**Errors:**
- `"Unknown mode '<m>'"` → valid: suggestions, gate
- `"protocol is required for mode='gate'"` → pass protocol parameter
- `"Protocol directory not found: protocol-testing/<p>"` → protocol name doesn't match directory structure

**When to use:** `mode="gate"` as a pre-commit check; `mode="suggestions"` during spec authoring for improvement hints.

---

### ivy_patterns
Pattern detection, validation, comparison, scaffold completeness, and template scaffolding.

| Field | Value |
|-------|-------|
| Parameters (analyze/validate/compare/check) | protocol (str), mode (str, "analyze"), pattern (str, None), reference_protocol (str, None) |
| Parameters (scaffold) | protocol (str), mode="scaffold", pattern (str), wire_format (str, "binary"), role_type (str, "asymmetric"), variant_names (list[str], None), roles (list[str], None) |
| Returns (analyze) | { patterns, total_patterns, mode } |
| Returns (validate) | { patterns, issues, validation_summary } |
| Returns (compare) | { protocol_a, protocol_b, comparison } |
| Returns (check) | { completeness_score, layers_present, layers_missing, suggestions, has_manifest } |
| Returns (scaffold) | { source, pattern, file_suggestion } |
| Timeout | 60s |
| Tier | fast |
| Rendering | raw |
| Concurrency | standard |

**Errors:**
- `"Unknown mode '<m>'"` → valid: analyze, validate, compare, check, scaffold
- `"Protocol directory not found: protocol-testing/<p>"` → wrong protocol name
- `"reference_protocol required for compare mode"` → add reference_protocol parameter
- `"Unknown pattern"` (scaffold mode) → valid patterns: serdes, variants, monitors, shim, module, entity
- Template substitution failure (scaffold mode) → protocol name contains characters unsupported in Ivy identifiers

**When to use:**
- `mode="analyze"` — enumerate the patterns currently present in a protocol (variants, monitors, shims, modules, entities). Use during Phase 1 exploration to get a quick pattern inventory before deciding what to add or change.
- `mode="validate"` — check the patterns already present for structural issues (missing guards, incomplete variants, unpaired serdes). Complements `ivy_diagnostics(mode="structural")`: diagnostics sees syntax, validate sees pattern-level correctness.
- `mode="compare"` — port patterns from a reference protocol (set via `reference_protocol`) to the target.
- `mode="check"` — audit a new protocol scaffold against the pattern library for completeness.
- `mode="scaffold"` — bootstrap a new layer file with ready-to-edit Ivy source.

---

## 7. Propagation

### ivy_propagation
Consolidated type propagation analysis: variant/struct enumeration (mode="variants"), serializer/deserializer correlation (mode="serdes"), and change impact categorization (mode="impact").

| Field | Value |
|-------|-------|
| Parameters (variants) | mode="variants", type_name (str), protocol (str, None) |
| Parameters (serdes) | mode="serdes", type_name (str), protocol (str, None) |
| Parameters (impact) | mode="impact", type_name (str), change_type (str), protocol (str, None) |
| Returns (variants, struct) | { type_name, kind, file, line, fields: [{ name, type, is_array }] } |
| Returns (variants, variant) | { type_name, kind, file, line, members: [{ name, tag, wire_type, fields }] } |
| Returns (serdes) | { type_name, correlations: [{ serializer, deserializer, instance }] } |
| Returns (impact) | { type_name, change_type, auto_propagate, manual_review, unaffected } |
| Timeout | 60s |
| Tier | fast (variants/serdes) / slow (impact) |
| Rendering | raw |
| Concurrency | needs_model=True |

**Errors:**
- `"type '<n>' not found in <dir>"` (variants/impact) → wrong type name or protocol; check exact Ivy identifier; verify with `ivy_propagation(mode="variants")` first
- `"Model is still building"` → retry in 30s
- Empty `correlations` (serdes) → no SERDES instance found for type; may be a non-message type
- Empty `auto_propagate` (impact, except type_def) → SERDES instance not found; check pattern library

**When to use:** `mode="variants"` as the first step in change-impact analysis — inspect type structure before adding a field or variant. `mode="serdes"` to locate serializer/deserializer files to update after adding a variant or field. `mode="impact"` before any type modification — get the full propagation map so no files are missed.

---

## 8. Workspace and State

### ivy_workspace
Manage the active Ivy protocol workspace scope.

| Field | Value |
|-------|-------|
| Parameters | action (str: set/get/list/clear), target (str, None), roles (str, None) |
| Returns (set) | { status, active_group, active_layers, granularity, files_in_scope } |
| Returns (get) | { status, active_group, active_layers, active_tests, granularity, set_by } |
| Returns (list) | { status, active_group, available_groups } |
| Returns (clear) | { status, active_group, active_layers } |
| Timeout | 10s |
| Tier | instant |
| Rendering | raw |
| Concurrency | local_only |

**Errors:**
- `"Unknown action '<a>'"` → valid: set, get, list, clear
- `"action='set' requires a 'target' parameter"` → add target
- `"Unknown workspace group '<g>'"` → use `action="list"` to see available groups

**When to use:** Scope verification and coverage tools to a specific protocol to prevent cross-protocol collisions.

---

### ivy_workflow_state
Manage workflow state files for multi-session tracking.

| Field | Value |
|-------|-------|
| Parameters | action (str), workflow (str, None), phase (str, None), protocol (str, None), caller (str, None), invocation_depth (int, 0), state (str/dict, None), event_type (str, None), last_n (int, 20) |
| Returns | { success, action, ... action-specific fields } |
| Timeout | 10s |
| Tier | instant |
| Rendering | raw |
| Concurrency | local_only |

**Errors:**
- `"Unknown action '<a>'"` → valid: set, get, clear, get_build, set_build, append_journal, get_journal
- `"action='set' requires 'workflow' parameter"` → add workflow
- `"Cannot resolve protocol directory"` → provide protocol or set workspace first
- `"Invalid event_type '<t>'"` → valid: session_start, session_end, decision, phase_transition, progress, error, context_switch

**When to use:** Read on every turn to know current workflow phase; write when transitioning phases in multi-session workflows.

**Journal event types (action="append_journal"):** validated against `_VALID_EVENT_TYPES` in both `hooks/scripts/workflow_state.py` and `ivy_lsp/mcp/tools/workflow_state.py`. Unknown types are rejected.

| Event type | Written by | Payload fields |
|------------|------------|----------------|
| `session_start` | workflow skills on entry | `resumed_from` |
| `session_end` | workflow skills at clean exit | `clean`, `phase_at_exit` |
| `decision` | workflow skills and user-confirmed choices | `summary`, arbitrary decision-specific keys |
| `phase_transition` | workflow skills at phase boundaries | `from`, `to` |
| `progress` | workflow skills during long-running steps | `detail` |
| `error` | `record-workflow-error.py` hook and workflow skills | `detail`, `implication`, `summary` |
| `context_switch` | navigate Phase 0 (plan-mode detection), other skills | `detection`, `mode` |
| `gate_dispatched` | gate-trigger hooks (`assess-modeling.py`, `route-user-prompt.py`, etc.) | `gate`, `trigger`, `artifact`, `layer`, `methodology` |
| `gate_verdict` | orchestrator after critic fan-out | `gate` ("g0".."g5"), `verdict`, `vote`, `patterns`, `cycle`, `tier`, `duration_s` |
| `plan_approved` | navigate Plan-Author Branch on ExitPlanMode | `workflow` (caller), `phase_before_plan`, `plan_file`, `supersedes` |
| `workflow_resumed` | navigate Phase 1.5 after G0 SOUND verdict | `workflow` (caller), `phase_after_resume`, `g0_cycle` |
| `knowledge_captured` | knowledge-capture skill after a capture cycle | `source`, `status` (`approved`/`user_declined`/`deferred`), `references_plan_approved_ts` |

Detailed payload shapes for `gate_verdict` live in the reflection-patterns skill (load via `Skill(skill="panther-ivy-plugin:cross-cutting-reflection-patterns")`; see "Gate verdict payload"). `plan_approved` and `workflow_resumed` are consumed by the navigate skill's Phase 1.5 (load via `Skill(skill="panther-ivy-plugin:workflow-navigate")`).

---

### ivy_index
Build or check the offline `.ivy-index/` for a protocol.

| Field | Value |
|-------|-------|
| Parameters | protocol (str, "all"), fast (bool, False), status (bool, False) |
| Returns | { summaries } or { status_reports } |
| Timeout | 300s |
| Tier | blocking |
| Rendering | raw |
| Concurrency | standard; invalidates model caches and refreshes staging on completion |

**Errors:**
- `"Index builder not available: <exc>"` → import error; ivy-lsp install incomplete
- Protocol not found → check `protocol-testing/<protocol>/` directory exists
- Stale staging after build → automatic; if tools still see old files, restart the MCP server

**When to use:** After adding or renaming `.ivy` files; required before `ivy_coverage` and `ivy_visualize(view="summary")` can see new content.

---

### ivy_iut_test
Run an Ivy test against a real IUT via PANTHER's experiment pipeline.

| Field | Value |
|-------|-------|
| Parameters | protocol (str), test_name (str), iut_name (str), version (str, ""), timeout (int, 120), extra_params (dict, None), config_path (str, None) |
| Returns | { verdict, test_name, iut_name, protocol, test_stdout, test_stderr, iut_logs, duration_seconds, output_dir, experiment_summary } |
| Timeout | 180s |
| Tier | blocking |
| Rendering | raw |
| Concurrency | standard; requires Docker |

**Errors:**
- `"panther CLI not found"` → `.venv/bin/panther` not found in ancestor dirs; activate venv first
- `"Protocol '<p>' not found at <dir>"` → wrong protocol name or plugin not installed
- `"IUT plugin '<n>' not found at <dir>"` → wrong iut_name; check `panther plugins list`
- `"Config error: <exc>"` → config_path file is invalid YAML or missing tests section
- `verdict == "timeout"` → increase timeout param; IUT may be slow to start

**When to use:** Final integration test after `ivy_compile` succeeds; requires a running Docker environment.
