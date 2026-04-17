---
paths: ["**/*.ivy", "**/*.spec", "**/*.py"]
---

### MCP Tool Name Reference

| Consolidated Tool | Mode / View / Detail | Key Parameters |
|---|---|---|
| `ivy_verify` | -- | relative_path, isolate |
| `ivy_compile` | -- | relative_path, target, isolate |
| `ivy_model_info` | -- | relative_path, isolate |
| `ivy_diagnostics` | mode="structural"\|"full" | relative_path, layers, min_severity |
| `ivy_diagnostics` | mode="dashboard" | protocol |
| `ivy_analysis` | mode="includes" | relative_path |
| `ivy_analysis` | mode="scope" | protocol |
| `ivy_status` | mode="capabilities" | -- |
| `ivy_status` | mode="health" | -- |
| `ivy_coverage` | mode="stats" | relative_path, test_file |
| `ivy_coverage` | mode="gaps" | test_file, protocol |
| `ivy_coverage` | mode="matrix" | relative_path, test_file |
| `ivy_extract_requirements` | -- | rfc_text |
| `ivy_extract_requirements` | output="manifest" | rfc_name, rfc_text |
| `ivy_visualize` | view="dependencies" | test_file |
| `ivy_visualize` | view="state_machine" | test_file |
| `ivy_visualize` | view="layers" | test_file |
| `ivy_visualize` | view="summary" | test_file |
| `ivy_visualize` | view="requirements" | action_name, file_path, test_file |
| `ivy_quality` | mode="suggestions" | file_path |
| `ivy_quality` | mode="gate" | protocol, gate_level |
| `ivy_patterns` | mode="analyze"/"validate"/"compare" | protocol, pattern |
| `ivy_patterns` | mode="check" | protocol |
| `ivy_patterns` | mode="scaffold" | protocol, pattern |
| `ivy_workspace` | action="set"\|"get"\|"list"\|"clear" | target (for set), roles (optional) |
| `ivy_index` | -- | protocol |
| `ivy_manifest` | -- | protocol |
| `ivy_propagation` | mode="variants" | type_name |
| `ivy_propagation` | mode="serdes" | type_name |
| `ivy_propagation` | mode="impact" | type_name, change_type |
| `ivy_workflow_state` | action="set" | workflow, phase, protocol, caller, invocation_depth |
| `ivy_workflow_state` | action="get" | protocol |
| `ivy_workflow_state` | action="clear" | protocol |
| `ivy_workflow_state` | action="get_build" | protocol |
| `ivy_workflow_state` | action="set_build" | protocol, state (JSON) |
| `ivy_rfc` | mode="get"\|"search"\|"section" | number, query, format, section, analyze, limit |

### Coverage Tool Scoping Parameters

The `ivy_coverage` tool (all modes: stats, gaps, matrix) accepts different scoping parameters:

| Parameter | Scoping Semantics | Use When |
|---|---|---|
| `relative_path` | Directory-prefix filtering — annotations in files under this path | Browsing a subdirectory |
| `test_file` | **Endpoint-mirror scoping** — transitive include closure of the test entry point | NCT-aligned per-endpoint coverage |
| `protocol` | Directory-prefix `protocol-testing/{protocol}/` | Filtering by protocol |

**Recommendation**: Use `test_file` for accurate NCT-aligned results. The include closure matches exactly the files PANTHER copies into the staging directory for a given test endpoint.

Example: `ivy_coverage(mode="stats", test_file="quic/quic_tests/client_tests/quic_client_test.ivy")` returns coverage scoped to the client endpoint mirror's include closure only.
