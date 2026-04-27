---
name: knowledge-ivy-writing-guide
description: "Use when writing or editing .ivy files. Provides Ivy 1.7 syntax reference, module system, RFC annotation conventions, test-spec patterns, and search-before-write practice."
user-invocable: false
context: fork
paths: "**/*.ivy"
---

# Ivy Writing Guide

**Type:** flexible — adapt principles to context.

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill combines the Ivy language reference, test specification patterns, and RFC bracket-tag annotation conventions. Use it whenever editing or creating `.ivy` files.

**Boundary with `specification-patterns`:** this skill owns *language-level* decisions (before/after monitor syntax, `around` / `require` / `_generating` semantics, serializer/deserializer patterns). `specification-patterns` owns *layer-decomposition* decisions (which file does a type belong in, which layer depends on which, 14-layer template). Load both when designing a new layer; load only this one when editing within a layer.

## Canonical Syntax

The canonical Ivy 1.7 syntax reference (types, relations, functions, individuals, actions, invariants, object system, module system, isolates, include directives, before/after monitors, state machines, shim bridges, RFC tags, weight attributes, RFC-to-Ivy mapping, test-spec template, generator patterns) lives in the project auto-memory as `~/.claude/projects/<project>/memory/reference_ivy_patterns.md` (moved from `.claude/rules/ivy-patterns.md` on 2026-04-23). The rule stub at that path still auto-loads for `**/*.ivy` paths and nudges Claude to `Read` the memory file. This skill does not restate the syntax; it adds the *practices* below to use alongside those canonical forms.

Every Ivy file begins with `#lang ivy1.7` as its first line (the version PANTHER standardizes on).

### Search Before Writing

Before introducing a new declaration of any kind, grep the relevant protocol tree for existing instances so your new form matches existing conventions:

- Relations: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Functions: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Actions: `Grep(pattern="action.*=", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Invariants: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Prefer to copy a working neighbor's shape over synthesizing a fresh declaration.

## Test Specification Patterns

Load `references/syntax-examples.md` for test spec structure, role isolation, weight attributes, and variant patterns.

### Test File Checklist

1. `#lang ivy1.7` header
2. Protocol stack includes
3. Shim include for the role Ivy plays
4. Entity behavior include
5. `after init` block with socket/TLS setup
6. `export` declarations
7. `_finalize` with end-state checks

## RFC Bracket-Tag Annotations

Tag every `require`, `ensure`, `assume`, or `assert` with bracket tags: `# [rfc9000:4.1]`

Load `references/syntax-examples.md` for annotation workflow, tag conventions, and requirement manifests.

## Common Pitfalls and Best Practices

### Pitfalls

1. **Forgetting `after init` blocks**: Relations and functions start with arbitrary values unless explicitly initialized.

2. **Ungrounded variables in invariants**: `invariant sent(P, N)` means "for all P and N, sent(P,N) is true" -- probably not what you intended.

3. **Overly strong invariants**: Too strong will fail on initial state. Start weak, strengthen as needed.

4. **Missing `require` clauses**: Without preconditions, actions can be called in any state.

5. **Circular includes**: Ivy does not support circular include dependencies.

6. **Using `assume` instead of `require`**: `assume` weakens the model by introducing unverified assumptions.

7. **Missing _finalize**: Without _finalize, end-state properties are never checked.

8. **Correct role convention**: Server test = Ivy plays client. File name reflects what is tested.

### Best Practices

1. **Name conventions**: `snake_case` for actions/relations/functions. `PascalCase` for module names.
2. **Small isolates**: Keep isolates focused on one component for easier solving.
3. **Incremental verification**: Verify incrementally — small changes are easier to debug than large batches.
4. **Document invariants**: Add comments explaining why each invariant is needed.
5. **Separate specification from implementation**: Use `specification` and `implementation` blocks.
6. **Use `after init`**: Explicitly initialize all mutable state.
7. **Minimize axioms**: Every axiom is an unverified assumption.

## Protocol Modeling Patterns

Load `references/generator-mechanics.md` for Z3 test generation mechanics, solver scope rules, and common generator pitfalls. Concrete protocol-modeling examples (client/server roles, boolean FSMs, packet-type hierarchies) live in `~/.claude/projects/<project>/memory/reference_ivy_patterns.md` (the `.claude/rules/ivy-patterns.md` stub points there).

## Common Syntax Traps

See the `ivy-error-patterns` skill for the full error-to-fix lookup table with code examples. Key traps:

- **Parameter name collision** — use single uppercase letter params (`S:type`), not descriptive names that collide with existing symbols
- **Missing `after init`** — relations start arbitrary; invariants fail on initial state
- **`assume` vs `require`** — `assume` weakens the model unsoundly; use `require` for preconditions
- **Ungrounded variables** — `invariant sent(P,N)` means "for all P,N"; bind variables explicitly
- **Overly strong invariants** — `invariant connected(C)` fails immediately; use conditional form

For detailed code examples of each trap, see the `ivy-error-patterns` skill.

## Integration

## C++ Serializer/Deserializer Patterns

Custom serializers extend `ivy_binary_ser_128` in `<<< impl` blocks. They are state machines that convert between Ivy struct/variant values and wire-format bytes.

Load `references/serializer-patterns.md` for:
- Base class method signatures and override rules (the base writes 16 bytes per `set`/`open_list`/`open_tag` — custom serializers MUST override these)
- Serialization vs deserialization callback sequences
- State machine design patterns
- Common pitfalls (signature mismatch, garbage injection, uninitialized locals)

---

- **LOADED BY:** build workflow (write phase)

**Related skills:**
- **specification-patterns** -- Where to place each declaration type (14-layer template)
- **methodology-reference** -- Verification after editing, RFC-to-Ivy mapping
- **ivy-toolkit** -- MCP tool documentation

**Related agents:**
- **model-reviewer** -- Reviews model quality
- **spec-analyst** -- Verification and diagnosis
