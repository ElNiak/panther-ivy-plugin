---
name: ivy-debugging-methodology
description: Use when debugging Ivy verification or compilation errors. Enforces a mandatory pre-fix research workflow. Must be followed before proposing any fix to an Ivy spec. Triggers on "debugging ivy", "fix ivy error", "verification failed", "compilation error", "ivy_check failed", "diagnose ivy", or any attempt to fix a failing Ivy specification.
---

# Ivy Debugging Methodology

## Hard Rule

You MUST complete steps 1-6 before proposing ANY fix. Skipping directly to a fix is forbidden.
If you cannot find a working example or skill reference that explains the error, say so explicitly rather than guessing.

## Mandatory Pre-Fix Checklist

### Step 1: Parse the Error

Extract from the error output:
- **Error type** (the key phrase: `not found`, `invariant failed`, `type mismatch`, etc.)
- **Line number** and **file path**
- **Symbol or construct** that failed

### Step 2: Diagnostic Interpretation Protocol

If the error came from `ivy_verify`, `ivy_lint`, or LSP diagnostics, read the **full `diagnostics` array**, not just `error_summary`.

Classify each diagnostic by its `source` field:

| Source | Layer | What It Means |
|--------|-------|---------------|
| `"ivy"` | Parser | Syntax or parse error in the Ivy file |
| `"ivy-lint"` | Structural | Fast structural check (braces, headers, includes) |
| `"ivy-lsp"` | LSP analysis | In-process semantic check (collisions, missing init) |
| `"ivy-lsp-reqs"` | Requirements | Requirement coverage gap |
| `"ivy-lsp-semantic"` | RFC tags | Orphaned or missing bracket tags |
| `"ivy-lsp-coverage"` | Coverage | Unmonitored actions or unguarded state |
| `"ivy_check"` | Verification | Full formal verification result |

**Priority cascade:** Fix Error-severity diagnostics first. Then Warning. Then Info/Hint.

When a diagnostic points to a specific line, read 5 lines above and below before forming a hypothesis.

### Step 3: Consult Skills

Load and check these skills for the failing construct:
- `ivy-error-patterns` — look up the specific error message substring
- `ivy-model-editing` — check syntax rules for the construct type (relation, function, action, invariant, etc.)

### Step 4: Run Linter

Call `ivy_lint` via MCP before running full verification:
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint(relative_path="<file>")
```
This runs in milliseconds and catches structural issues (missing `#lang`, unmatched braces, unresolved includes, parameter name collisions, missing init) without the cost of full `ivy_check`.

### Step 5: Search Existing Models for Working Examples

Use `Grep` to find similar constructs in `protocol-testing/`:

- For `relation` issues: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/")`
- For `function` issues: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/")`
- For `after init` issues: `Grep(pattern="after init", glob="*.ivy", path="protocol-testing/")`
- For `invariant` issues: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/")`
- For `action` issues: `Grep(pattern="^action |^    action ", glob="*.ivy", path="protocol-testing/")`

**Prioritize models for the same protocol family** (e.g., when debugging BGP, search `protocol-testing/bgp/` first).

### Step 6: Formulate Theory

Before editing anything, state a specific hypothesis:
- "The error `'src' not found` occurs because Ivy resolves parameter names as symbols. Existing QUIC models use single uppercase letters (C, S, P). The fix is to rename `src` to `S`."

The theory MUST reference evidence from steps 2-5. If you have no evidence, say so.

### Step 7: Apply Minimal Fix

Only now propose a change. Make it minimal — change only what's needed to fix the specific error.

### Step 8: Verify

Run verification to confirm the fix:
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify(relative_path="<file>")
```
If the fix introduces new errors, return to Step 1 for the new error.
