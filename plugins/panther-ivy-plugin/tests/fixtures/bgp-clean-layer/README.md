# bgp-clean-layer fixture

Minimal BGP layer chain used by `evals/workflow_dispatch_eval.json` verify cases (clean-layer pass, counterexample diagnosis, compile-error abstain, G4 SOUND).

## Contents

- `bgp_header_message.ivy` — BGP header layer (RFC 4271 Section 4.1)
- `bgp_open_message.ivy` — OPEN message layer (RFC 4271 Section 4.2)
- `bgp_keepalive_message.ivy` — KEEPALIVE layer (RFC 4271 Section 4.4)

The three files together exercise the header to (open + keepalive) chain — the smallest BGP slice that supports a verify Phase 4 / G4 SOUND outcome.

## Source

Files are exact copies (no modification) of the live tree at
`panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/`
captured for stable eval input.

## Used by

- `evals/workflow_dispatch_eval.json` — verify cases (4), build cases (4), review cases (3), and the gate-firing cases that reference this fixture path.
- `evals/gate_critic_outcome_eval.json` — gate dispatch loci that cite the BGP layers as evidence anchor.
