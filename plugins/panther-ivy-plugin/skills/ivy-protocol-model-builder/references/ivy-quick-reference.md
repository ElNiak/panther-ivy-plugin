# Ivy Language Quick Reference

Collected from all phases for quick lookup during model development.

| Construct | Syntax | Purpose |
|---|---|---|
| Type (abstract) | `type query_id` | Declare a new type |
| Type (bit-vector) | `interpret query_id -> bv[16]` | Give type a concrete representation for compilation |
| Enumeration | `type rcode = {noerror, formerr}` | Finite set of values |
| Alias | `alias aid = cid` | Type alias |
| Definition | `definition zero = 0` | Named constant |
| Struct | `type this = struct { f : T }` | Composite data type |
| Variant | `variant this of base = struct { f : T }` | Subtype of a base type (dispatched at runtime) |
| Array | `instance arr : array(idx, this)` | Array type for a struct |
| Relation | `relation seen(C:cid)` | Boolean predicate |
| Function | `function count(C:cid) : nat` | Value mapping |
| Individual | `individual ep : ip.endpoint` | Singleton value (scoped to module instance) |
| Parameter | `parameter addr : ip.addr = 0x0a000001` | Command-line-settable value |
| Action | `action event(src, dst, msg) = {}` | Protocol event (body defined by advice) |
| Import action | `import action show_debug(x:T)` | Action implemented in C++ (for debug output) |
| Around advice | `around event(params) { ... }` | Wrap action with pre/post conditions |
| Before advice | `before event(params) { ... }` | Precondition check |
| After advice | `after event(params) { ... }` | Side effect / state update |
| Require | `require expr` | Assertion (test fails if false) |
| Not / And / Or | `~expr`, `e1 & e2`, `e1 \| e2` | Boolean operators |
| `_generating` | `if _generating { ... }` | Guard for tester-generated events |
| Export | `export action_name` | Make action available to random testing |
| Weight | `attribute action.weight = "5"` | Bias random selection (higher = more frequent) |
| Finalize | `export action _finalize = { ... }` | End-of-test assertions (called by runtime) |
| Module | `module name(params) = { ... }` | Parameterized code template |
| Instance | `instance x : module(args)` | Module instantiation |
| Include | `include filename` | Textual file insertion (no `.ivy` suffix) |
| Init | `after init { ... }` | Initialization block |
| Bit operations | `bvand(x, mask)`, `bfe[lo][hi](x)` | Bitwise AND, bit-field extraction |

For comprehensive Ivy syntax coverage, consult the `ivy-writing-guide` skill.
