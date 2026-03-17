# Ivy Writing Guide — Extended Reference

This file contains extended Ivy language examples moved from the SKILL.md to reduce its size. The SKILL.md retains the core language reference, test spec patterns, RFC annotations, and common pitfalls.

## Axioms and Conjectures

```ivy
axiom connected(X, Y) -> connected(Y, X)     # Assumed true (not checked)
conjecture forall P. sent(P, dest(P)) -> ack_pending(P)  # Checked but not inductive
```

Axioms are unverified assumptions — minimize their use. Conjectures are checked but not used inductively in proofs.

## Type `this` (Extended Example)

Inside an object, `type this` declares the object itself as a parameterized type:
```ivy
object counter = {
    type this
    individual val(X: this) : nat
    action increment(c: this) = { val(c) := val(c) + 1 }
}
```

This allows creating instances of the object type and passing them as parameters.

## Nested Objects (Extended Example)

```ivy
object protocol = {
    object client = {
        action connect(srv: server.endpoint)
    }
    object server = {
        type endpoint
        action accept(c: client)
    }
}
```

Nested objects create hierarchical namespaces. Cross-references between nested siblings use dotted names.
