---
name: nct-methodology
description: "Use when working with NCT (Network-Centric Compositional Testing) - specification-based protocol compliance testing with Ivy formal models. Covers core concepts, directory structure, checkpoints, and common mistakes. Chains to ivy-workflow-orchestrator for spec creation."
---

<HARD-GATE>
Do NOT write any Ivy code or scaffold any spec files until you have completed
Phase 1 (Explore) and Phase 2 (Plan) via the ivy-workflow-orchestrator skill.
</HARD-GATE>

## Iron Laws
1. NO SPEC WRITING without completed requirement extraction
2. NO COMPILATION without passing verification
3. ALWAYS chain to ivy-workflow-orchestrator for spec creation/modification
4. ALWAYS use ivy-toolkit for tool operations (never direct CLI)

## NCT -- Network-Centric Compositional Testing

### Overview

NCT is a specification-based testing methodology where a formal Ivy protocol specification plays one role (client, server, or man-in-the-middle) against an Implementation Under Test (IUT). The specification generates test traffic via Z3/SMT symbolic execution and monitors received packets against formal assertions.

### Core Concepts

#### Role Inversion
The Ivy tester's role is the **opposite** of what it tests:
- Testing a server IUT -> Ivy acts as a formal client (`{prot}_server_test_*.ivy` files)
- Testing a client IUT -> Ivy acts as a formal server (`{prot}_client_test_*.ivy` files)
- MIM testing -> Ivy acts as man-in-the-middle (`{prot}_mim_test_*.ivy` files)

**Rule:** File name indicates WHAT IS TESTED. `quic_server_test_*.ivy` = testing the server, Ivy plays client.

#### Specification Structure
Protocol specs use **monitors** (before/after clauses) attached to protocol events:

- **before clauses** -- Preconditions/guards. Define what must hold before an event occurs. If the precondition fails, the event is blocked.
- **after clauses** -- State updates/checks. Record history by updating shared variables. Check specification compliance of received data.
- **_finalize()** -- End-state verification. Called when the test completes. Performs heuristic checks (e.g., data was received, no errors occurred).

#### Test Traffic Generation
Specifications use `export` to declare actions that the test mirror generates randomly. Z3/SMT solving ensures generated traffic complies with specification constraints. `import` actions are provided by the IUT.

### NCT Workflow (Summary)

The full 10-step workflow is documented in `references/nct-workflow-detail.md`. Summary:

| Phase | Steps | Gate |
|-------|-------|------|
| **Explore** | 1. Select protocol/RFC, 2. Extract requirements | Requirements manifest produced |
| **Plan** | 3. Decompose into 14-layer template, 4-5. Design type + stack layers | Layer mapping reviewed |
| **Build** | 6-8. Entity roles, behavioral constraints, test specs | Each file passes `ivy_lint` |
| **Verify** | 9. `ivy_verify` + `ivy_compile` (target=test) | Zero verification errors |
| **Execute** | 10. Run against IUT via PANTHER | Results collected |

### Directory Structure

```
protocol-testing/{prot}/
|-- {prot}_stack/          # Core protocol model (layers 1-9)
|-- {prot}_entities/       # Entity definitions and behavior
|-- {prot}_shims/          # Implementation bridge
|-- {prot}_utils/          # Serialization, utilities
+-- {prot}_tests/
    |-- server_tests/      # Tests targeting server IUTs
    |-- client_tests/      # Tests targeting client IUTs
    +-- mim_tests/         # Man-in-the-middle tests
```

**Naming**: `{prot}_{layer}.ivy` for stack layers, `ivy_{prot}_{role}.ivy` for entities, `{prot}_{role}_test_*.ivy` for tests.

### Tools

See **ivy-toolkit** skill for all tool documentation.

### Checkpoints -- Verify Before Continuing

| Checkpoint | Condition to Meet |
|------------|-------------------|
| Type layer complete | Types are the foundation -- all other layers depend on them being defined first. |
| Verification passes | Verify after every meaningful change -- errors compound when deferred. |
| RFC consulted | RFC is the source of truth for every requirement and assertion. |
| Bracket tags present | Every assertion has a `# [rfcNNNN:X.Y]` tag for traceability. |
| Role inversion correct | Testing a server = Ivy acts as client. File names reflect what is tested. |
| `_finalize` exported | End-state properties require `_finalize` to execute. |

### Common Mistakes

**Missing `after init`**
- **Problem:** Relations/functions start with arbitrary values, not defaults
- **Fix:** Always include `after init` block setting initial state for all relations

**Correct role assignment**
- **Convention:** Server test files = Ivy plays client (opposite of what is tested)
- **Rule:** File name indicates WHAT IS TESTED. `quic_server_test_*.ivy` = testing the server, Ivy plays client.

**Missing bracket tags on assertions**
- **Problem:** Assertions lack `[rfcNNNN:X.Y]` comments, breaking traceability
- **Fix:** Tag every `require`/`ensure`/`assert` with its RFC section reference

**Ungrounded variables in invariants**
- **Problem:** `invariant sent(P, N)` means "for ALL P and N, sent is true"
- **Fix:** Quantify explicitly or bind variables to specific values

**Forgetting to export `_finalize`**
- **Problem:** End-state checks never execute
- **Fix:** Always include `export action _finalize` in test specifications

## Integration
- **CHAINS TO:** ivy-workflow-orchestrator (for deep mode -- spec creation/modification)
- **LOADS:** ivy-toolkit (for all tool operations)
- **DISPATCHES:** spec-analyst (Phase 1), traceability-agent (Phase 2), methodology-guide (Phase 3)
- **FAST MODE:** For concept questions about NCT, use this skill directly without orchestrator
- **DEEP MODE:** For spec work, invoke ivy-workflow-orchestrator which loads this skill at Phase 1

## Reference Files
- **references/nct-workflow-detail.md** -- Full 10-step NCT workflow with code examples
- **references/quic-canonical-example.md** -- QUIC protocol canonical walkthrough
