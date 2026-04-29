# Pre-fix debugging methodology

The mandatory checklist Claude follows before proposing a fix to a verification or compilation failure. The host skill (`verification-failures`) points here whenever `ivy_verify` / `ivy_check` fails and a fix is being prepared.

## Hard rule

The checklist below is mandatory because fixes proposed without evidence from it are flagged UNSOUND by the G4 verification gate. If no working example or skill reference explains the error, say so explicitly rather than guessing.

## Mandatory pre-fix checklist

### Step 1: Parse the error

Extract from the error output:
- **Error type** (the key phrase: `not found`, `invariant failed`, `type mismatch`, etc.)
- **Line number** and **file path**
- **Symbol or construct** that failed

### Step 2: Diagnostic interpretation protocol

If the error came from `ivy_verify`, `ivy_diagnostics`, or LSP diagnostics, read the **full `diagnostics` array**, not just `error_summary`.

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

**Priority cascade:** Fix Error-severity diagnostics first. Then Warning. Then Info / Hint.

When a diagnostic points to a specific line, read 5 lines above and below before forming a hypothesis.

### Step 3: Consult skills

Load and check these skills for the failing construct:

- The host skill's `## Error-pattern catalog` section — look up the specific error message substring.
- `ivy-syntax` — check syntax rules for the construct type (relation, function, action, invariant, etc.).

### Step 4: Run structural check

Call `ivy_diagnostics` in structural mode before full verification. It runs in milliseconds and catches structural issues (missing `#lang`, unmatched braces, unresolved includes, parameter name collisions, missing `init`) without the cost of `ivy_verify`. Canonical invocation shape: load `Skill(skill="panther-ivy-plugin:ivy-toolkit")` and consult `references/tool-invocation-examples.md`.

### Step 5: Search existing models for working examples

Use `Grep` to find similar constructs in `protocol-testing/`:

- For `relation` issues: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/")`
- For `function` issues: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/")`
- For `after init` issues: `Grep(pattern="after init", glob="*.ivy", path="protocol-testing/")`
- For `invariant` issues: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/")`
- For `action` issues: `Grep(pattern="^action |^    action ", glob="*.ivy", path="protocol-testing/")`

**Prioritize models for the same protocol family** (e.g., when debugging BGP, search `protocol-testing/bgp/` first).

### Step 6: Formulate theory

Before editing anything, state a specific hypothesis:

- "The error `'src' not found` occurs because Ivy resolves parameter names as symbols. Existing QUIC models use single uppercase letters (C, S, P). The fix is to rename `src` to `S`."

The theory MUST reference evidence from steps 2–5. If you have no evidence, say so.

### Step 7: Apply minimal fix

Only now propose a change. Make it minimal — change only what's needed to fix the specific error.

### Step 8: Verify

Run verification to confirm the fix. For the canonical invocation shape, load the ivy-toolkit skill via `Skill(skill="panther-ivy-plugin:ivy-toolkit")` and consult its `tool-invocation-examples` reference. If the fix introduces new errors, return to Step 1 for the new error.

## Serializer / deserializer debugging

For C++ serializer state machine issues (wrong bytes on wire, `deser_err` throws, state machine stuck), load the `ivy-syntax` skill and read `references/serializer-patterns.md`.

## Self-evaluation reference

`debugging-environment.md` (sibling file in the same `references/` directory) — self-evaluation protocol (anti-pattern checklist), debug environment variables, LSP indexing awareness. For the full 9-step health-check runbook (log paths, common failures, process liveness), dispatch the triage agent via `Agent(subagent_type="panther-ivy-plugin:ivy-triage-agent", prompt="Run the 9-step Ivy LSP + MCP health-check runbook.")`.
