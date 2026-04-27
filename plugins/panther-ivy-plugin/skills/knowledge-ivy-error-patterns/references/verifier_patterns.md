# Verifier Patterns Catalog

Numbered, append-only catalog of failure patterns that adversarial quality gates cite by ID. Sparse IDs preserve source-section provenance; do not renumber. Each `[GAP: #NN]` marker refers to an entry here.

Owned by the `ivy-error-patterns` skill. The orchestrator and critics access this catalog via that skill — either by loading it through the Skill tool or by having the orchestrator read it and embed relevant slices into spawned-critic prompts.

## Entry format

Every entry has five fields:

- **#NN: short title** (≤ 8 words)
- **Trigger:** one sentence — when does this failure manifest?
- **What to check:** one sentence — what the critic reads or greps for.
- **Source:** paper section, doc URL, or `feedback_*` memory ID.
- **Methodology tag:** one of `NCT` | `NACT` | `NSCT` | `Ivy` | `Plugin-Memory`.

## ID ranges per lifecycle gate

| Range | Gate(s) | Topic |
|---|---|---|
| #100-149 | G1, G5 | NCT base lifecycle failures |
| #150-199 | G1 | NACT attacker-model and mutation failures (NACT overlay) |
| #200-249 | G2, G3, G4 | Ivy decidability and testing-tutorial patterns |
| #250-299 | G2, G3, G4 | Plugin-memory migrations (learned in-house patterns) |
| #260-289 | G2 | NSCT timer and topology (NSCT overlay) |
| #300-399 | G3 | Test-spec authoring patterns |
| #400-499 | G4 | Verification verdict patterns |
| #500-559 | G5 | Trace-analysis patterns |
| #560-589 | G5 | NSCT replay and syscall (NSCT overlay) |

Per-gate slices (canonical):

- **G1**: `#100-149` + (`#150-199` if NACT) + `#250-299` (subset relevant to scope/blueprint).
- **G2**: `#200-249` + `#250-299` + (`#260-289` if NSCT).
- **G3**: `#200-208` + `#256-259` + `#300-399`.
- **G4**: `#200-249` + `#250-299` + `#400-499`.
- **G5**: `#100-107` + `#500-559` + (`#560-589` if NSCT).

Gates load only their range slice plus the active methodology overlay. The active methodology comes from `build-state.yaml`'s `methodology` field. NCT-tagged entries always load; NACT entries load when `methodology: nact`; NSCT entries load when `methodology: nsct`.

---

## #100-149 — NCT base lifecycle failures

<catalog_entry>
### #100: Burst packet generation triggers false congestion
- **Trigger:** IUT under test sends packets in tight bursts during NCT runs.
- **What to check:** Packet inter-arrival times in pcap; look for round-trip-time spikes correlated with congestion-control state changes that would not occur on a real wire.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Limitations of NCT.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #101: Verification latency exceeds protocol response window
- **Trigger:** Tester takes longer to check an incoming packet than the protocol's response deadline allows.
- **What to check:** Wall-clock duration between recv and the corresponding send in tester logs; compare against the RFC-mandated timeout for that message type.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Limitations of NCT.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #102: Network nondeterminism across runs
- **Trigger:** Same Ivy spec + same IUT produces different traces on re-run.
- **What to check:** Diff two runs' `ivy_tester.log` event streams; any reordering not attributable to a deliberate scheduler choice is a reproducibility bug.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Limitations of NCT.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #103: IUT nondeterminism unmasked
- **Trigger:** Crash bug exists in IUT but only fires on some runs.
- **What to check:** Whether replay with identical seed reproduces the crash; if not, NCT cannot pin the trigger.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Limitations of NCT.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #104: Manual mutation generation does not scale
- **Trigger:** Adding a new protocol or new mutation class requires hand-written spec edits.
- **What to check:** Are mutation operators encoded as reusable rules in a manifest, or are they one-off edits per protocol?
- **Source:** Crochet et al. arXiv:2503.01538 §Discussion.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #105: Untested attacker composability
- **Trigger:** Multiple attacker specs defined in isolation; combined-attacker scenarios not exercised.
- **What to check:** Does the test matrix include MitM + malicious-client cross product, or only single-attacker runs?
- **Source:** Crochet et al. arXiv:2503.01538 §Step 2.
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #106: Single-vantage observation only
- **Trigger:** Compositional test instruments only one endpoint; off-path observers absent.
- **What to check:** Number of pcap capture points in the run directory; presence of an off-path tap in the topology.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Limitations (motivation for Shadow).
- **Methodology tag:** `NCT`

</catalog_entry>

<catalog_entry>
### #107: Specification-implementation drift
- **Trigger:** Spec updated for new RFC text but mutation library not regenerated.
- **What to check:** Timestamp comparison: spec file mtime vs mutation-set mtime; absence of a CI gate that re-derives mutations on spec change.
- **Source:** Crochet et al. arXiv:2503.01538 §Step 1.
- **Methodology tag:** `NCT`

---

</catalog_entry>

## #150-199 — NACT attacker-model and mutation failures

<catalog_entry>
### #150: Version negotiation injection abuse
- **Trigger:** IUT processes version-negotiation packets after a connection is partially established.
- **What to check:** lsquic-style flow — does receiving a VN packet (e.g., 0xff00001d) trigger checksum failure or session reset post-handshake?
- **Source:** Crochet et al. arXiv:2503.01538 §Reproduced vulnerabilities (lsquic).
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #151: Memory exhaustion via repeated-frame parsing
- **Trigger:** Malformed NEW_TOKEN or NEW_CONNECTION_ID frames sent in quantity.
- **What to check:** IUT resident-memory growth across N malformed frames; presence of a bounded-allocation invariant in the spec.
- **Source:** Crochet et al. arXiv:2503.01538 §Reproduced vulnerabilities (quant).
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #152: Infinite loop on malformed frame during close
- **Trigger:** Malformed frame arrives concurrent with CONNECTION_CLOSE.
- **What to check:** CPU-bound spin in the close path; the spec must cap iteration count in the close handler.
- **Source:** Crochet et al. arXiv:2503.01538 §Reproduced vulnerabilities (quant).
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #153: Repeated CONNECTION_CLOSE not idempotent
- **Trigger:** A second CONNECTION_CLOSE arrives after the first.
- **What to check:** State machine accepts the duplicate close without re-entering the error path; the spec's close action has an idempotency invariant.
- **Source:** Crochet et al. arXiv:2503.01538 §Engineer-mistake list.
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #154: Encryption key on wrong epoch post-VN
- **Trigger:** Version negotiation completes; a subsequent packet is sent with pre-VN keys.
- **What to check:** Key-schedule transition logic; the spec asserts that post-VN packets re-derive keys.
- **Source:** Crochet et al. arXiv:2503.01538 §Engineer-mistake list.
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #155: Payload validation gap (format-string class)
- **Trigger:** A protocol field documented as "opaque bytes" is passed to a formatter.
- **What to check:** MiniP-style ping handler — does the payload reach `printf`-family or logging without sanitization in the IUT code path?
- **Source:** Crochet et al. arXiv:2503.01538 §Example mutation (MiniP ping).
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #156: Boundary-value mutation gap
- **Trigger:** Spec uses small concrete bounds; max/min values are untested.
- **What to check:** Are mutation operators producing 0, MAX, MAX+1, MIN-1 for every numeric field?
- **Source:** Crochet et al. arXiv:2503.01538 §Step 1 mutation techniques.
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #157: Control-flow mutation not exercised
- **Trigger:** Spec branches are reachable but the mutation suite skips control-flow swaps.
- **What to check:** Coverage report of which spec branches got both their original and negated form tested.
- **Source:** Crochet et al. arXiv:2503.01538 §Step 1.
- **Methodology tag:** `NACT`

</catalog_entry>

<catalog_entry>
### #158: Missing malicious-server role
- **Trigger:** Test suite has malicious-client scenarios but no malicious-server peer for the IUT-as-client case.
- **What to check:** Coverage of the three-role taxonomy (MitM, malicious-client, malicious-server) per IUT role.
- **Source:** Crochet et al. arXiv:2503.01538 §Step 2 taxonomy.
- **Methodology tag:** `NACT`

---

</catalog_entry>

## #200-249 — Ivy decidability and testing-tutorial patterns

<catalog_entry>
### #200: Function symbol cycle (non-stratified)
- **Trigger:** Two or more function symbols form a directed cycle in the type graph (e.g., `f: t -> t` plus `g: t -> t`).
- **What to check:** Build the function-symbol arc graph from declarations; any cycle causes Z3 deepening-instantiation timeout.
- **Source:** [ivy/decidability](https://microsoft.github.io/ivy/decidability.html) §Stratification.
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #201: Universal-then-existential quantifier alternation
- **Trigger:** `forall x. exists y. P(x, y)` appears in an invariant or spec.
- **What to check:** Skolemization introduces a function symbol; verify no new arc closes a cycle. Look for divergence of the form `f(y) > y, f(f(y)) > f(y), …`.
- **Source:** [ivy/decidability](https://microsoft.github.io/ivy/decidability.html).
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #202: Arithmetic on universally quantified variables
- **Trigger:** `forall x. x + 1 < bound` or similar arithmetic on a bound variable.
- **What to check:** Restrict arithmetic literals to FAU shapes (`X < Y`, `X < t`, `t < X`, `X = t` with `X, Y` universals and `t` ground), positive occurrence only.
- **Source:** [ivy/decidability](https://microsoft.github.io/ivy/decidability.html) §FAU.
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #203: Non-recursive definition unfolds outside FAU
- **Trigger:** Helper definition that, when inlined, places a nested function application on a universal variable.
- **What to check:** Unfold each definition by hand; confirm the result still satisfies FAU bounds.
- **Source:** [ivy/decidability](https://microsoft.github.io/ivy/decidability.html) §Definitions.
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #204: Biconditional invariant without modular separation
- **Trigger:** Invariant uses `<->` and the predicate appears both positively and negatively.
- **What to check:** Split into one-way implications across isolate boundaries to limit Z3 instantiation.
- **Source:** [ivy/decidability](https://microsoft.github.io/ivy/decidability.html).
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #205: Missing export starves random generator
- **Trigger:** Action defined but never `export`ed; the generator has nothing to call at this interface.
- **What to check:** For every action expected to drive the IUT, confirm an `export` declaration exists. No export = silent tester at that interface.
- **Source:** [ivy/testing/specification](https://microsoft.github.io/ivy/examples/testing/specification.html).
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #206: `require` / `ensure` role confusion
- **Trigger:** Spec author writes `ensure` where `require` is needed (or vice versa) on an exported action's `before` monitor.
- **What to check:** For exported actions, `before` monitor assertions are *assumptions* on the environment (they constrain the generator); inside an implementation body they are *guarantees*. Verify each assertion's role matches the role of the object owning it.
- **Source:** [ivy/testing/specification](https://microsoft.github.io/ivy/examples/testing/specification.html) guarantee/assumption paragraph.
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #207: Trusted isolate masquerading as proved
- **Trigger:** Isolate marked `trusted=true` but downstream consumers treat its lemmas as proved.
- **What to check:** Audit `trusted` flags; `trusted` means tested-only, not formally verified — propagate that uncertainty to dependents.
- **Source:** [ivy/testing/leader](https://microsoft.github.io/ivy/examples/testing/leader.html) ("verified informally by testing").
- **Methodology tag:** `Ivy`

</catalog_entry>

<catalog_entry>
### #208: Generator over-constrained by stacked `require`s
- **Trigger:** Many `require` clauses on an exported action; Z3 cannot find a satisfying parameter assignment.
- **What to check:** Tester silence on that action despite an `export` declaration. Relax or split `require`s; verify none reference state Z3 cannot solve for (Z3 samples action params, not state vars).
- **Source:** [ivy/testing/leader](https://microsoft.github.io/ivy/examples/testing/leader.html) ("selecting actions consistent with the history").
- **Methodology tag:** `Ivy`

---

</catalog_entry>

## #250-299 — Plugin-memory migrations

<catalog_entry>
### #250: Solver re-entry flood
- **Trigger:** Exported handle action without a re-entry guard; Z3 floods the generator with parallel invocations.
- **What to check:** The handle action begins with `require ~present` (or equivalent single-entry guard).
- **Source:** `feedback_ivy_solver_reentry_guards`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #251: Dual-purpose event needs disjunctive guard
- **Trigger:** An event is used for both "incoming at A" and "incoming at B"; a single guard cannot express both meanings.
- **What to check:** Guards on dual-purpose events should be disjunctive (`require guard_a | guard_b`); FRR state-race memory has a concrete example.
- **Source:** `feedback_ivy_event_semantics`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #252: `deser_err` uncaught crashes binary
- **Trigger:** Deserializer can emit `deser_err` but the caller has no handler.
- **What to check:** Every message variant's deserializer is followed by a `deser_err` check or caught at the first exported boundary; otherwise the tester core-dumps.
- **Source:** `feedback_ivy_deser_error_handling`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #253: Trusted isolate `NativeAction` leak
- **Trigger:** `ivy_check` sees trusted sub-isolates but their `NativeAction`s leak into `mod.actions`.
- **What to check:** Verify `ivy_isolate.py:1880` patch is applied; or inspect the module's action list for actions from trusted sub-isolates without `verified=True`.
- **Source:** `feedback_ivy_check_trusted_isolate`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #254: `bv[16]` not interpreted for time arithmetic
- **Trigger:** Spec declares a time type and performs arithmetic on it but omits the `interpret seconds -> bv[16]` clause.
- **What to check:** For every numeric time type used in a `+` / `<` expression, an `interpret ... -> bv[N]` line exists; otherwise Z3 cannot reason about the arithmetic.
- **Source:** `feedback_ivy_bv16_seconds`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #255: Z3 sets action params but not state
- **Trigger:** A `require` in an exported `before` references state (e.g., `require self.connected`), not the action's parameters.
- **What to check:** Rewrite so the constraint is on the action param; or pass the state-derived value as a parameter.
- **Source:** `feedback_ivy_solver_params_vs_state`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #256: Frame queuing requires composite exports
- **Trigger:** Spec tries to send a composite message by calling a single action; the generator only fires atomic events.
- **What to check:** For composite messages, export a `handle+enqueue+message_event` triple (QUIC pattern) so the generator can build up the composite.
- **Source:** `feedback_ivy_quic_queuing_pattern`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #257: Serializer base-class override missing
- **Trigger:** Custom serializer inherits from `ivy_binary_ser` but overrides only some methods.
- **What to check:** `ivy_binary_ser_128` writes 16 bytes per `set / open_list / open_tag`; override ALL methods, not just `set`.
- **Source:** `feedback_ivy_ser_base_class`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #258: Parameterized object missing `me` scope
- **Trigger:** Parameterized object defines an action without binding `me` to the instance parameter.
- **What to check:** For each parameterized object, every action body that references instance fields is wrapped in `me` or passed the parameter explicitly.
- **Source:** `feedback_ivy_parameterized_objects`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #259: Atomic auto-send omitted in after-block
- **Trigger:** Spec handles a message in `after` but doesn't enqueue/emit the corresponding outgoing event atomically.
- **What to check:** `after` blocks for receive actions include the atomic single-event send pattern (QUIC model), not a deferred timer or external loop.
- **Source:** `feedback_ivy_autosend_pattern`.
- **Methodology tag:** `Plugin-Memory`

---

</catalog_entry>

## #260-299 — NSCT timer and topology

<catalog_entry>
### #260: Non-reproducible burst timing
- **Trigger:** IUT timer fires depend on host wall clock rather than the simulated clock.
- **What to check:** Replay same seed twice; identical timer-fire sequence required. Confirm the timer interface is routed through Ivy's time module, not `gettimeofday` directly.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Time interface.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #261: Busy-loop precision loss
- **Trigger:** IUT or tester uses a busy-wait instead of a sleep syscall.
- **What to check:** Shadow only intercepts syscalls; busy loops bypass simulated time. Grep IUT and harness for spin loops in timing-critical paths.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Time primitives.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #262: Time-unit mismatch at interface
- **Trigger:** Spec declares a timer in seconds; IUT expects milliseconds (or microseconds).
- **What to check:** Each call site of `start_timer` / `sleep` — confirm declared unit (seconds, ms, μs) matches both sides.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Time interface units.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #263: Time breakpoint absent at deadline event
- **Trigger:** Spec asserts "response within T" but no temporal breakpoint is scheduled at T.
- **What to check:** Time-varying property requires an explicit breakpoint; otherwise the tester never evaluates the assertion at the deadline.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Time breakpoints.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #264: Blocking vs non-blocking sleep mismatch
- **Trigger:** Spec uses non-blocking sleep; downstream code assumes blocking semantics (or vice versa).
- **What to check:** Each sleep call site — confirm the chosen variant matches caller expectation; mixed-mode causes silent reordering under Shadow.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Time primitives.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #265: Topology omits links present in deployment
- **Trigger:** Shadow topology file is sparser than the real deployment graph.
- **What to check:** Compare Shadow topology to the deployment diagram; missing links hide partition and relay attacks.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Shadow integration.
- **Methodology tag:** `NSCT`

---

</catalog_entry>

## #300-399 — Test-spec authoring patterns

<catalog_entry>
### #301: Exported handle without re-entry guard
- **Trigger:** A handle action is `export`ed but lacks the single-entry guard; the generator floods it with parallel invocations.
- **What to check:** Every `export handle_*` action begins with `require ~present` (or protocol-equivalent) before any state mutation.
- **Source:** `feedback_ivy_solver_reentry_guards` (G3-specific framing; complements #250).
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #302: `require` becomes assumption in exported `before`
- **Trigger:** Author writes `require X = Y` in an exported `before` monitor intending a proof obligation; because the monitor is on an exported action, Z3 treats it as a constraint on the generator, not as an obligation — so the model is effectively unsound wherever the equality does not hold at runtime.
- **What to check:** For exported actions, `require` in `before` is an assumption. If a runtime check is intended, convert to `ensure`.
- **Source:** `feedback_ivy_test_compilation`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #303: `_finalize` omitted for terminal state
- **Trigger:** Test spec declares exports for the happy path but no `_finalize` to check the end state.
- **What to check:** Every `*_test_*.ivy` has exactly one `_finalize` body; that body contains at least one `require` on each terminal relation.
- **Source:** Plugin convention; ivy-writing-guide skill (load via `Skill(skill="panther-ivy-plugin:knowledge-ivy-writing-guide")`), syntax-examples reference.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #304: Exports cover happy path only
- **Trigger:** Exported actions exercise the protocol's nominal flow but not error or boundary cases.
- **What to check:** Coverage matrix from `ivy_coverage(mode="matrix")`: every MUST requirement is tied to at least one exported action; error-handling MUSTs in particular are not orphaned.
- **Source:** `ivy-writing-guide` + coverage-gap memory.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #305: `_finalize` not grounded in requirement set
- **Trigger:** `_finalize` body checks implementation-detail relations instead of the RFC-derived requirement set.
- **What to check:** Each `_finalize require`/`ensure` line has a corresponding `[rfcNNNN:X.Y]` annotation; unannotated checks are candidates for removal or re-derivation.
- **Source:** Plugin convention; `methodology-reference`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #306: Requirement-side evaluation incomplete
- **Trigger:** A requirement covers both generate and receive sides but the spec tests only one side.
- **What to check:** For every `require` whose RFC text applies bidirectionally, the test spec exercises both the generate path (exported sender) and the receive path (monitor on the inbound).
- **Source:** `feedback_requirement_side_evaluation`.
- **Methodology tag:** `Plugin-Memory`

---

</catalog_entry>

## #400-499 — Verification verdict patterns

<catalog_entry>
### #401: Unsound `assume` collapses obligation
- **Trigger:** Spec contains an `assume` that was used as a shortcut when a `require` should have been proved.
- **What to check:** Grep for every `assume` in the verified file; each must have a documented rationale. An `assume true`, an `assume` on a complex predicate, or any `assume` added "to get verify to pass" is a likely unsound shortcut.
- **Source:** Plugin convention; `model-reviewer` anti-pattern.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #402: `ivy_verify` passes but trusted sub-isolate leaked actions
- **Trigger:** `ivy_verify` returns `status: OK`, but the verified isolate depends on a trusted sub-isolate whose `NativeAction`s are propagated unverified.
- **What to check:** Inspect the isolate graph; any `trusted=true` ancestor whose `NativeAction`s appear in the verified isolate's `mod.actions` implies the OK verdict is conditional on unverified code.
- **Source:** `feedback_ivy_check_trusted_isolate`; `ivy_isolate.py:1880`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #403: Error whitelisted via comment-out
- **Trigger:** A `require` or `invariant` has been commented out, weakened, or replaced with `true` to get the verifier green.
- **What to check:** Git diff of the verified file since the last SOUND verdict; any removed or weakened `require`/`invariant` without a `// RESOLVED` or `// DEFERRED` comment at that site is a whitelisting fix.
- **Source:** `feedback_no_error_whitelisting`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #404: Solver wall claimed sound
- **Trigger:** `ivy_verify` hits a solver wall (Z3 timeout, unsat core not found, or a known-blocker pattern) and the orchestrator claimed `SOUND` anyway.
- **What to check:** `ivy_verify` return schema — `status: OK` with `duration_s` near the `timeout` parameter, or `counterexample_trace` indicating Z3 gave up, is never `SOUND`. Correct verdict is `ABSTAIN` with `abstain_reason: solver wall`.
- **Source:** Memory: `bgp-as-path-solver-blocker`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #405: Pre-fix research skipped
- **Trigger:** A proposed fix for a verification failure is presented without the 6 mandatory research steps from `ivy-debugging-methodology` (diagnostics by source layer, skill consultation, linter run, working-example search, theory formulation, minimal-fix selection).
- **What to check:** The preceding conversation or workflow journal contains completed steps 1-6 before any `Edit`/`Write` on the verified file.
- **Source:** `skills/ivy-debugging-methodology/SKILL.md` steps 1-6.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #406: Missing four-layer diagnostic cascade
- **Trigger:** A failure was diagnosed by reading only the `ivy_verify` output without consulting `ivy-lint`, `ivy-lsp`, `ivy-lsp-semantic`, or `ivy-lsp-coverage` layers.
- **What to check:** The diagnostic record names the layer that produced each finding; omitted layers suggest the root cause is in a layer the critic did not read.
- **Source:** `skills/ivy-debugging-methodology/SKILL.md`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #410: Missing guard (counterexample classification)
- **Trigger:** Counterexample reaches an action without a required precondition being true; a state variable the assertion depends on is never set.
- **What to check:** The trace's first step shows an action firing without a `require` in its `before` clause that should be present; e.g., `stream.send` fires while `connected = false`.
- **Source:** `skills/counterexample-guide/SKILL.md` §Common Failure Patterns: Missing Guard.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #411: Uninitialized state (counterexample classification)
- **Trigger:** Counterexample shows a state variable with an unexpected value at Step 1, before any action has modified it; no `after init` block sets it.
- **What to check:** Grep the spec for `after init` blocks; every relation/function used in an assertion must have an explicit initialization.
- **Source:** `skills/counterexample-guide/SKILL.md` §Common Failure Patterns: Uninitialized State.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #412: Incorrect monitor scope (counterexample classification)
- **Trigger:** A monitor (`before`/`after` block) is attached to the wrong action, so the constraint never fires when the action it should protect runs; counterexample shows the unconstrained action.
- **What to check:** For each constraint cited in the counterexample, confirm the monitored action name matches the action firing in the trace. Wrong action attachment or wrong `mixin_kind` (`before` vs `after`) is the fix site.
- **Source:** `skills/counterexample-guide/SKILL.md` §Common Failure Patterns: Incorrect Monitor Scope.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #413: Invariant too strong (counterexample classification)
- **Trigger:** Invariant fires during an intermediate step of a multi-step transition; the state is correct at start and end but transient state violates the invariant.
- **What to check:** Counterexample steps show the invariant holds at Step N-1 and Step N+1 but breaks at Step N; the invariant does not account for a legitimate transition phase. Weaken or move check to `_finalize`.
- **Source:** `skills/counterexample-guide/SKILL.md` §Common Failure Patterns: Invariant Too Strong.
- **Methodology tag:** `Plugin-Memory`

---

</catalog_entry>

## #500-559 — Trace-analysis patterns

<catalog_entry>
### #500: Verdict taken from summary without reading trace
- **Trigger:** A G5 conclusion cites `analysis/ivy_tester_results.json` alone without opening `logs/ivy_tester/ivy_tester.log`.
- **What to check:** The critic's output references specific trace events by timestamp or line number; a verdict that does not is premature.
- **Source:** Plugin convention (G5 read-order).
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #501: Ivy trace claims event, pcap shows nothing
- **Trigger:** `ivy_tester.log` records a send event at time T; the corresponding `pcaps/*.pcap` has no matching wire-level frame within [T, T+jitter].
- **What to check:** Use `tshark -r <pcap> -Y '<protocol filter>'` and timestamp-align with the trace; a send event in Ivy without a pcap frame is either a spec auto-send that bypasses the wire or a lost IUT transmission.
- **Source:** `feedback_crossvalidate_ivy_pcap`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #502: Four-stream analysis skipped
- **Trigger:** G5 conclusion is presented without reading all four log streams (ivy-trace, IUT log, IUT stderr, pcap).
- **What to check:** The report cites evidence from each of the four streams; missing stream indicates an incomplete diagnosis per the 9-step procedure.
- **Source:** `feedback_iut_output_analysis`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #503: RFC quoted partially in finding
- **Trigger:** Finding cites `[rfcNNNN:X.Y]` but truncates the normative quote, dropping MUST / SHOULD / MAY text.
- **What to check:** Each `[rfcNNNN:X.Y]` citation is followed by the complete sentence from the RFC including every normative keyword, matching the `.claude/rules/ivy-formatting.md` convention.
- **Source:** `feedback_rfc_quotes_complete`; `feedback_always_quote_rfc`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #504: Bug presented without triangulation
- **Trigger:** A bug finding lacks at least one of: direct code quote, full RFC quote, or a diagram/schema.
- **What to check:** Finding body contains a code block, a verbatim RFC quote, and (for protocol bugs) a state/sequence diagram; all three together.
- **Source:** `feedback_bug_presentation`.
- **Methodology tag:** `Plugin-Memory`

</catalog_entry>

<catalog_entry>
### #505: Model bug attributed to IUT
- **Trigger:** A counterexample is explained as an IUT violation without first ruling out a model bug.
- **What to check:** The diagnostic procedure explicitly considered "model bug" as a hypothesis and checked the spec for each candidate pattern (e.g., #250, #251, #255, #306) before concluding IUT fault.
- **Source:** `skills/counterexample-guide`.
- **Methodology tag:** `Plugin-Memory`

---

</catalog_entry>

## #560-589 — NSCT replay and syscall

<catalog_entry>
### #560: Replay seed not pinned
- **Trigger:** Test-harness invocation does not pass an explicit seed; default randomness varies per run.
- **What to check:** CLI invocation captures seed in run metadata; replay command can reproduce a bit-identical trace.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Reproducibility.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #561: Network-jitter parameter undocumented per run
- **Trigger:** Shadow link latency/jitter set globally; per-test override silently inherited.
- **What to check:** Per-run config records the latency/jitter values used; defaults without explicit override are flagged.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Shadow parameters.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #562: Computation budget unbounded per packet
- **Trigger:** No upper bound on tester verification time per incoming packet.
- **What to check:** Add a per-packet wall-clock cap; failures imply the spec must simplify toward FAU (cross-ref #101 and #202).
- **Source:** Rousseaux et al. arXiv:2503.04810 §Verification latency.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #563: Syscall not in Shadow's intercept set
- **Trigger:** IUT uses a time-related syscall (e.g., `RDTSC`, `clock_gettime` variant) not intercepted by Shadow.
- **What to check:** Every time-related syscall used by the IUT appears in Shadow's documented intercept list; otherwise wall-clock leaks into the test.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Shadow syscall interception.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #564: Live-debug hook left enabled in CI
- **Trigger:** Shadow live-debugging hook remains attached during automated runs.
- **What to check:** CI config disables interactive debug; presence of the hook skews timing reproducibility.
- **Source:** Rousseaux et al. arXiv:2503.04810 §Shadow debugging.
- **Methodology tag:** `NSCT`

</catalog_entry>

<catalog_entry>
### #565: Time-syscall interception mismatched
- **Trigger:** Spec time interface routes through C++ `time.h` wrapper, but the IUT links a different libc path that bypasses Shadow.
- **What to check:** Both sides resolve through the same intercepted syscall surface; otherwise spec and IUT see different clocks.
- **Source:** Rousseaux et al. arXiv:2503.04810 §C++ time.h interception.
- **Methodology tag:** `NSCT`

---

</catalog_entry>

## Convention: adding new entries

- Append to the relevant range section. Never renumber.
- Pick an ID at least 3 higher than the previous last-used in the range, to leave room for provenance-preserving insertions.
- If an entry is deprecated (superseded by a better pattern or source error), mark the title with `[DEPRECATED]` and add a `See:` pointer to the replacement. Do not delete.
- A pattern with no verified source does not belong in this catalog. Every entry must cite either a published paper, an official doc, or a `feedback_*` memory ID.
