# Common pitfalls, best practices, and syntax traps

Cross-cutting Ivy-language pitfalls Claude should avoid when authoring or editing protocol specs. The host skill (`ivy-syntax`) points here when verifying *language-level* decisions; defer to `ivy-error-patterns` for the full error-to-fix lookup table with code examples.

## Common Pitfalls

1. **Forgetting `after init` blocks**: Relations and functions start with arbitrary values unless explicitly initialized.

2. **Ungrounded variables in invariants**: `invariant sent(P, N)` means "for all P and N, sent(P,N) is true" — probably not what you intended.

3. **Overly strong invariants**: Too strong will fail on initial state. Start weak, strengthen as needed.

4. **Missing `require` clauses**: Without preconditions, actions can be called in any state.

5. **Circular includes**: Ivy does not support circular include dependencies.

6. **Using `assume` instead of `require`**: `assume` weakens the model by introducing unverified assumptions.

7. **Missing _finalize**: Without _finalize, end-state properties are never checked.

8. **Correct role convention**: Server test = Ivy plays client. File name reflects what is tested.

## Best Practices

1. **Name conventions**: `snake_case` for actions/relations/functions. `PascalCase` for module names.
2. **Small isolates**: Keep isolates focused on one component for easier solving.
3. **Incremental verification**: Verify incrementally — small changes are easier to debug than large batches.
4. **Document invariants**: Add comments explaining why each invariant is needed.
5. **Separate specification from implementation**: Use `specification` and `implementation` blocks.
6. **Use `after init`**: Explicitly initialize all mutable state.
7. **Minimize axioms**: Every axiom is an unverified assumption.

## Common Syntax Traps

For the full error-to-fix lookup table with code examples, load the `ivy-error-patterns` skill.

- **Parameter name collision** — use single uppercase letter params (`S:type`), not descriptive names that collide with existing symbols
- **Missing `after init`** — relations start arbitrary; invariants fail on initial state
- **`assume` vs `require`** — `assume` weakens the model unsoundly; use `require` for preconditions
- **Ungrounded variables** — `invariant sent(P,N)` means "for all P,N"; bind variables explicitly
- **Overly strong invariants** — `invariant connected(C)` fails immediately; use conditional form
