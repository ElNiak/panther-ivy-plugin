# Methodology-reference — glossary

Eight Ivy / methodology terms used across `methodology` without further definition.

| Term | Definition |
|---|---|
| NCT | Normal Compliance Testing. The default methodology: test an IUT against RFC normative requirements (`MUST` / `SHOULD` / `MAY`). Workflow path: `build` → `verify` → `review`. Reference skills loaded: `specification-patterns`, `ivy-syntax`, `verification-failures`. |
| NACT | Normal Adversarial Compliance Testing. Security-focused: model an attacker, prove the IUT either resists the attack or detect the violation. Workflow path: `build` (with `apt-attack-patterns` scope) → `verify`. Adds the APT 6-stage attack lifecycle and around-block monitors. |
| NSCT | Normal Simulation Compliance Testing. Network-condition / replay scenarios using the Shadow Network Simulator. Workflow path: `build` → emit experiment-config sidecar at Phase 6. The methodology adds NSCT-overlay catalog patterns `#260-289` (G2) and `#560-589` (G5). |
| isolate | Ivy module unit; a syntactic boundary that owns a set of actions, types, relations, and invariants. Isolates compose via `assume`/`guarantee` contracts. The 14-layer template makes each layer a separate isolate. |
| monitor (`before` / `after`) | Pre- or post-condition block attached to an action; the verifier checks the monitor body against the action's transition. `before` enforces preconditions (with `require`); `after` enforces post-state invariants (with `require` or assignments). |
| `_finalize` action | Special action that runs at end-of-trace to check end-state properties. Use this instead of an `invariant` when the property holds only at trace termination, not at every intermediate step. |
| Role inversion | When testing an IUT that plays role X, the Ivy spec plays role ~X. Testing a QUIC *server* means Ivy plays the *client* (`quic_server_test_*` files generate client-side test traffic). The `oppose_role()` mapping handles this. |
| `export` / `import` | Isolate-level visibility: `export` exposes an action across the assume-guarantee boundary; `import` declares an action belongs to the environment (the IUT) and is observable but not controlled. The verifier may assume `import`-ed actions but must guarantee `export`-ed ones. |
