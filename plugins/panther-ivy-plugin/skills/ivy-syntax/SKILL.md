---
name: ivy-syntax
description: "Use when writing or editing .ivy files. Provides Ivy 1.7 syntax reference, module system, RFC annotation conventions, test-spec patterns, and search-before-write practice."
user-invocable: false
context: fork
paths: "**/*.ivy"
---

# Ivy Writing Guide

**Type:** flexible — adapt principles to context.

> **Workspace**: Set active workspace with `/set-workspace <protocol>` for protocol-scoped operations.

This skill covers *language-level* decisions for `.ivy` files: before/after monitor syntax, `require` / `_generating` semantics, serializer/deserializer patterns, RFC bracket-tag annotations, and the search-before-write practice.

**Boundary with `specification-patterns`:** this skill owns *language-level* decisions. `specification-patterns` owns *layer-decomposition* decisions (which file does a type belong in, which layer depends on which, 14-layer template). Load both when designing a new layer; load only this one when editing within a layer.

## Canonical Syntax

The canonical Ivy 1.7 syntax reference (types, relations, functions, individuals, actions, invariants, object system, module system, isolates, include directives, before/after monitors, state machines, shim bridges, RFC tags, weight attributes, RFC-to-Ivy mapping, test-spec template, generator patterns) lives in the project auto-memory as `~/.claude/projects/<project>/memory/reference_ivy_patterns.md`. The rule stub at the canonical-rules path still auto-loads for `**/*.ivy` paths and nudges Claude to `Read` the memory file.

Every Ivy file begins with `#lang ivy1.7` as its first line.

### Search Before Writing

Before introducing a new declaration of any kind, grep the relevant protocol tree for existing instances:

- Relations: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Functions: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Actions: `Grep(pattern="action.*=", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
- Invariants: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Prefer to copy a working neighbor's shape over synthesizing a fresh declaration.

## Reference dispatch

| When | Read |
|---|---|
| Test-spec structure, role isolation, weight attributes, variant patterns | `references/syntax-examples.md` |
| RFC bracket-tag annotations (workflow, conventions, manifests) | `references/syntax-examples.md` |
| Z3 generation mechanics, solver scope rules, generator pitfalls | `references/generator-mechanics.md` |
| C++ serializer / deserializer patterns (signatures, callbacks, state-machine design) | `references/serializer-patterns.md` |
| Common pitfalls, best practices, syntax traps | `references/pitfalls.md` |
| Concrete protocol-modeling examples (client/server roles, FSMs, packet hierarchies) | `~/.claude/projects/<project>/memory/reference_ivy_patterns.md` |

For the full error-to-fix lookup table with code examples, load the `ivy-error-patterns` skill.

## Test File Checklist

1. `#lang ivy1.7` header
2. Protocol stack includes
3. Shim include for the role Ivy plays
4. Entity behavior include
5. `after init` block with socket/TLS setup
6. `export` declarations
7. `_finalize` with end-state checks

## Integration

- **Loaded by:** build workflow (write phase).
- **Related skills:** `specification-patterns` (layer placement), `methodology` (RFC mapping), `ivy-toolkit` (MCP tool docs), `ivy-error-patterns` (error catalog).
- **Related agents:** `model-reviewer` (quality), `spec-analyst` (verification + diagnosis).
