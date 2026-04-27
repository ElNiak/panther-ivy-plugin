# Tool Invocation Examples

Single source of truth for ivy-tools MCP parameter shapes that exceed brief inline narrative. Other skills cite this file via the `Skill` tool when they need a multi-line invocation block or a long inline signature; brief mentions like `ivy_diagnostics(mode="structural")` in tables and narrative prose may stay in place.

## ivy_diagnostics

Modes: `structural` | `full` | `dashboard` | `collisions`.

Structural (fast pre-verification check; milliseconds):
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics(
  relative_path="<file>",
  mode="structural"
)
```
Catches missing `#lang`, unmatched braces, unresolved includes, parameter-name collisions, missing `init`. Run before every `ivy_verify` to short-circuit failure feedback in milliseconds.

Full (5-layer; tens of seconds), dashboard (Phase 4 reporting), collisions (cross-workspace symbol-collision scan) follow the same call shape with `mode="full"`, `mode="dashboard"`, or `mode="collisions"`.

## ivy_verify

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify(
  relative_path="<file>"
)
```
Returns a structured verdict; on FAIL, populates a `diagnostics` array. Timeout policy and the full output schema are in `references/timing-and-concurrency.md` (slow tier). The PreToolUse hook injects a tip recommending `ivy_diagnostics(mode="structural")` first; honour it.

## ivy_propagation

Modes: `variants` | `serdes` | `impact`.

Impact (canonical change-impact analysis):
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_propagation(
  type_name="<type>",
  change_type="add_field|add_variant",
  mode="impact"
)
```
Returns the `auto_propagate` / `manual_review` / `unaffected` classification. Single source of truth for which files to edit on a type change; see `.claude/rules/propagation-authority.md` for the full rule set. The skill must not independently classify files.

Variants and serdes modes use the same call shape with `mode="variants"` or `mode="serdes"`. Both are FAST tier and do not require the impact-mode arguments.

## ivy_iut_test

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test(
  protocol="<protocol>",
  test_name="<test>",
  iut_name="<iut>"
)
```
The active workspace must be set via `ivy_workspace(action="set", target="<protocol>")` before invocation. Exit-code interpretation and the 9-step output analysis procedure are documented in the `verify` skill's `references/iut-output-analysis.md`.

## ivy_compile

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile(
  relative_path="<file>",
  target="test"
)
```
Produces a test-mode binary. Compilation failures return `diagnostics`; consult the `ivy-debugging-methodology` skill for the pre-fix research workflow.

## See also

- `references/tool-catalog.md` — per-tool parameters, errors, tiers, rendering.
- `references/timing-and-concurrency.md` — performance tiers, timeouts, concurrency model.
- `references/error-reference.md` — cross-cutting error patterns and recovery.
- `references/hook-lifecycle.md` — full PreToolUse / PostToolUse hook pipeline that wraps these tools.
