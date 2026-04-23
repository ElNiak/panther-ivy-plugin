# Tool-renderer formatter sketches — S-2 (deferred)

**Status:** deferred from a 2026-04-21 plugin audit session. The four tool-renderer formatters below were sketched against guessed output schemas; finalizing them requires calling each tool once on a real BGP isolate to confirm actual response keys, then tuning truncation thresholds and per-workflow branching.

## Context

`hooks/scripts/render-tool-result.py` registers formatters for only 5 of the plugin's 18 MCP tools (`ivy_verify`, `ivy_coverage`, `ivy_diagnostics`, `ivy_compile`, `ivy_quality`). For the other 13, raw JSON passes through to the agent context unformatted — the main function silently exits at line 263-265 when `FORMATTERS.get(base_tool)` returns `None`.

The audit flagged the gap as suggestion severity but singled out four high-value additions where formatters would meaningfully save context:

| Tool | Why |
|------|-----|
| `ivy_rfc` | can return large RFC text blocks (full RFC or section) |
| `ivy_model_info` | can return long type / relation / action lists for complex models |
| `ivy_visualize` | returns ASCII diagrams that benefit from truncation past ~60 lines |
| `ivy_analysis` | returns file lists (includes / scope) that want counts + top N |

Dropped from the priority list: `ivy_status`, `ivy_workspace`, `ivy_workflow_state`, `ivy_patterns`, `ivy_propagation`, `ivy_manifest`, `ivy_index`, `ivy_extract_requirements`, `ivy_iut_test` — these return small structured dicts where pass-through is acceptable.

## Signature

All formatters match the existing pattern in `render-tool-result.py`:

```python
def format_<tool>(data: dict, workflow: str | None) -> str | None
```

- `data`: parsed tool output dict
- `workflow`: active workflow name from `get_active_workflow(protocol_dir)` (one of `build`, `verify`, `review`, `triage`, or `None`)
- Return `str` to inject as additional context
- Return `None` to skip formatting (raw output passes through)
- Error pass-through pattern: `if "error" in data and <no-success-key> in data: return None`

## Sketches

### `format_ivy_rfc`

```python
def format_ivy_rfc(data: dict, workflow: str | None) -> str | None:
    """Collapse large RFC payloads; surface metadata + head of text."""
    if "error" in data and "text" not in data and "matches" not in data:
        return None

    rfc_number = _safe_get(data, "rfc_number", _safe_get(data, "number", "?"))
    mode = _safe_get(data, "mode", "get")

    if mode == "search" or "matches" in data:
        matches = data.get("matches", [])
        if not matches:
            return f"ivy_rfc search [RFC{rfc_number}]: 0 matches"
        head = "\n".join(
            f"  - §{m.get('section', '?')}: {(m.get('text') or '')[:80]}..."
            for m in matches[:5]
        )
        more = f"\n  ... (+{len(matches) - 5} more)" if len(matches) > 5 else ""
        return f"ivy_rfc search [RFC{rfc_number}]: {len(matches)} match(es)\n{head}{more}"

    section = _safe_get(data, "section", "all")
    text = data.get("text", "")
    if not text:
        return None

    if len(text) > 2000 and workflow != "build":
        return (
            f"ivy_rfc [RFC{rfc_number} §{section}]: {len(text)} chars "
            f"(first 800):\n\n{text[:800]}\n\n... (truncated)"
        )
    return f"ivy_rfc [RFC{rfc_number} §{section}]:\n\n{text}"
```

### `format_ivy_model_info`

```python
def format_ivy_model_info(data: dict, workflow: str | None) -> str | None:
    """Show counts + top symbols; collapse definitions."""
    if "error" in data and "types" not in data:
        return None

    isolate = _safe_get(data, "isolate", "(none)")
    types = data.get("types", [])
    relations = data.get("relations", [])
    actions = data.get("actions", [])
    functions = data.get("functions", [])

    if workflow == "triage":
        return (
            f"ivy_model_info [{isolate}]: "
            f"{len(types)} types, {len(relations)} relations, "
            f"{len(actions)} actions"
        )

    def _summarize(name: str, items: list, limit: int = 10) -> str:
        names = [str(i) for i in items[:limit]]
        more = f" (+{len(items) - limit} more)" if len(items) > limit else ""
        return f"  {name} ({len(items)}): {', '.join(names)}{more}"

    lines = [f"ivy_model_info [isolate={isolate}]"]
    lines.append(_summarize("types", types))
    lines.append(_summarize("relations", relations))
    lines.append(_summarize("actions", actions))
    if functions:
        lines.append(_summarize("functions", functions))
    return "\n".join(lines)
```

### `format_ivy_visualize`

```python
def format_ivy_visualize(data: dict, workflow: str | None) -> str | None:
    """Pass through diagrams; collapse if oversized."""
    if "error" in data and not any(k in data for k in ("diagram", "visualization", "output")):
        return None

    view = _safe_get(data, "view", "?")
    diagram = data.get("diagram") or data.get("visualization") or data.get("output") or ""
    if not diagram:
        return None

    line_count = diagram.count("\n") + 1
    if workflow == "triage":
        return f"ivy_visualize [{view}]: {line_count} lines rendered"

    if line_count > 60 and workflow != "build":
        head = "\n".join(diagram.split("\n")[:40])
        return (
            f"ivy_visualize [{view}, {line_count} lines, first 40]:\n\n"
            f"{head}\n\n... (truncated)"
        )
    return f"ivy_visualize [{view}]:\n\n{diagram}"
```

### `format_ivy_analysis`

```python
def format_ivy_analysis(data: dict, workflow: str | None) -> str | None:
    """Show counts + top files; collapse long lists."""
    if "error" in data and "files" not in data and "includes" not in data:
        return None

    mode = _safe_get(data, "mode", "?")
    files = data.get("files", []) or data.get("includes", []) or []

    if workflow == "triage":
        return f"ivy_analysis [{mode}]: {len(files)} files"

    if not files:
        return f"ivy_analysis [{mode}]: no files in scope"

    lines = [f"ivy_analysis [mode={mode}]: {len(files)} file(s)"]
    for f in files[:15]:
        path = f.get("path", "?") if isinstance(f, dict) else str(f)
        lines.append(f"  - {path}")
    if len(files) > 15:
        lines.append(f"  ... (+{len(files) - 15} more)")
    return "\n".join(lines)
```

### Registration diff

```python
FORMATTERS = {
    "ivy_verify": format_ivy_verify,
    "ivy_coverage": format_ivy_coverage,
    "ivy_diagnostics": format_ivy_diagnostics,
    "ivy_compile": format_ivy_compile,
    "ivy_quality": format_ivy_quality,
    "ivy_rfc": format_ivy_rfc,                # new
    "ivy_model_info": format_ivy_model_info,  # new
    "ivy_visualize": format_ivy_visualize,    # new
    "ivy_analysis": format_ivy_analysis,      # new
}
```

## Before implementing — required tool-output sampling

Call each tool once on a real BGP isolate, capture the response, and compare against the sketches' assumed keys. Record the actual keys observed in a followup table below.

### Suggested sample commands

| Tool | Command to sample |
|------|------|
| `ivy_rfc` | `ivy_rfc(mode="section", number=4271, section="6.1")` — exercises the `section` path |
| `ivy_rfc` | `ivy_rfc(mode="search", number=4271, query="MUST")` — exercises the `matches` path |
| `ivy_model_info` | `ivy_model_info(relative_path="bgp/bgp_stack/bgp_fsm.ivy")` |
| `ivy_visualize` | `ivy_visualize(view="layers", test_file="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update_announce.ivy")` |
| `ivy_analysis` | `ivy_analysis(mode="scope", protocol="bgp")` |

### Keys to confirm

| Formatter | Keys guessed | Confirm actual |
|---|---|---|
| `format_ivy_rfc` | `rfc_number` / `number`, `mode`, `text`, `matches`, `section` | |
| `format_ivy_model_info` | `isolate`, `types`, `relations`, `actions`, `functions` | |
| `format_ivy_visualize` | `view`, `diagram` / `visualization` / `output` | |
| `format_ivy_analysis` | `mode`, `files` / `includes`, each entry is dict with `path` or str | |

## Truncation thresholds (judgment calls)

Baseline thresholds in the sketches, ready for tuning after sampling:

| Tool | Threshold | Rationale |
|---|---|---|
| `ivy_rfc` | 2000 chars ⇒ truncate to 800 chars | single-section view fits in ~800 chars; full RFC requires `build` workflow for full passthrough |
| `ivy_model_info` | 10 symbols per category | readable in one eyeful; `triage` gets count-only |
| `ivy_visualize` | 60 lines ⇒ truncate to 40 lines | diagrams compress poorly; `build` gets full |
| `ivy_analysis` | 15 files | scope analysis is navigational; longer lists go to `Read` |

## Per-workflow branching — current coverage

Existing formatters have four explicit workflow branches (`build`, `verify`, `review`, `triage`). My sketches have two (triage vs everything else). Decide per tool whether additional branches are needed:

| Tool | Build | Verify | Review | Triage | Default |
|---|---|---|---|---|---|
| `ivy_rfc` | full text | truncate | truncate | n/a | truncate |
| `ivy_model_info` | full list | full list | full list | counts only | full list |
| `ivy_visualize` | full diagram | truncate | truncate | counts only | truncate |
| `ivy_analysis` | full list | truncate | truncate | counts only | full list |

## Next session checklist

When resuming S-2:

1. Read this file.
2. Call the five sample commands listed above; save each tool's output to compare against the "Keys guessed" column.
3. Fix any key mismatches in the sketches.
4. Tune truncation thresholds if sampling shows they're wrong for typical BGP output sizes.
5. Apply the formatters into `render-tool-result.py` (add four functions, extend `FORMATTERS` dict).
6. Verify via a PostToolUse invocation on one call per tool in each of the four workflows (drive workflow via `ivy_workflow_state(action="set", ...)`); confirm the formatted output renders correctly and errors still pass through.
7. Commit with message like `feat(hooks): add renderers for ivy_rfc / ivy_model_info / ivy_visualize / ivy_analysis`.

## Out of scope for this work

- Formatters for the 9 remaining MCP tools (`ivy_status`, `ivy_workspace`, `ivy_workflow_state`, `ivy_patterns`, `ivy_propagation`, `ivy_manifest`, `ivy_index`, `ivy_extract_requirements`, `ivy_iut_test`) — small-dict tools where pass-through is acceptable per the audit.
- Refactoring the `FORMATTERS` registration pattern (e.g., decorator-based) — current dict-based form is fine.
- Adding a fallback "pretty-print JSON" renderer for unmapped tools — discussed and decided against; silent pass-through is correct for small dicts.
