# PR Review: panther-ivy-plugin

**Branch**: `fix/nct-validate-ground-truth-and-scoping-docs`
**Changes**: 162 files, ~16,423 insertions, ~3,914 deletions
**Reviewed**: 2026-04-15

---

## Critical Issues (must fix)

### Security

1. **[code-reviewer] Shell command injection via Python string interpolation** — `scripts/workspace-common.sh:17,75,126` and `hooks/scripts/detect-ivy-workspace.sh:75`. Paths containing single quotes break out of Python string literals passed to `python3 -c`. Fix: pass values via `sys.argv[1]` or stdin.

2. **[code-reviewer] SessionEnd hook kills ALL sessions' servers** — `hooks/scripts/cleanup-ivy-lsp.sh:9-17`. Iterates all `*.pid` files instead of filtering by session tag, breaking multi-session isolation. Fix: filter by `*-${_SESSION_TAG}-*.pid`.

### Logic Bugs

3. **[code-reviewer] Shell hooks parse wrong JSON schema (no-ops in production)** — `hooks/scripts/block-direct-ivy.sh:21` and `post-write-ivy-lint.sh:20`. Read `d.get('command','')` at root level instead of `d.get('tool_input',{}).get('command','')`. Tests mask this by using incorrect input schema. Fix: nest into `tool_input`.

4. **[code-reviewer] `find_protocol_dir` returns protocol-testing root as fallback** — `hooks/scripts/workflow_state.py:125`. When no protocol is found, returns `protocol-testing/` itself, corrupting multi-protocol state. Fix: return `None`.

5. **[comment-analyzer] CLAUDE.md says PostToolUse "runs" diagnostics** — Line 86. The hook only emits a suggestion, never calls the MCP tool. Misleads Claude into thinking checks are already happening.

### Silent Failures

6. **[silent-failure-hunter] Circuit-breaker MCP health monitor swallows all exceptions** — `hooks/scripts/observability/observe.py:241`. `except Exception: pass` on the entire function body. MCP crash protection silently becomes non-functional.

7. **[silent-failure-hunter] "Non-blocking" hooks can crash on workflow state writes** — 6+ hooks promise `exit 0` but have no top-level try/except, while calling `workflow_state.py` functions that raise on file I/O errors. PreToolUse hooks could block tool execution.

### Test Failures

8. **[test-analyzer] 8 tests failing on branch** — 7 from filesystem isolation issues (hooks find real `active-workflow` files), 1 from SIGPIPE. These are deterministic failures that mask real behavioral coverage gaps.

---

## Important Issues (should fix)

### Logic Bugs

9. **[code-reviewer] `workflow_state.py` unconditional `import yaml` with no fallback** — Line 13. Hooks run in host Python which may lack pyyaml. Crashes all 8+ hooks that import this module.

10. **[comment-analyzer] CLAUDE.md omits `append_journal` and `get_journal` actions** — Lines 69. All 5 workflow skills reference these actions but tool reference doesn't document them.

11. **[comment-analyzer] Triage SKILL.md references wrong PID file paths** — Lines 47,159,217,258. Points to `/tmp/ivy-lsp-*.pid` instead of `/tmp/ivy-lsp-pids/*.pid`.

### Silent Failures

12. **[silent-failure-hunter] Bare `except:` catches SystemExit/KeyboardInterrupt** — `detect-ivy-workspace.sh:110` inline Python. Fix: use `except Exception:`.

13. **[silent-failure-hunter] stderr captured into variables corrupting downstream logic** — `block-direct-ivy.sh:21` and `post-write-ivy-lint.sh:20` use `2>&1`. Python warnings prepend to extracted values. Fix: use `2>/dev/null`.

14. **[silent-failure-hunter] Circuit breaker state write silently fails** — `check-mcp-health.py:58`. `except OSError: pass` means failure counter never increments, breaker resets permanently.

15. **[silent-failure-hunter] Session ID resolver failure completely silent** — `hook_utils.py:26-27`. `except Exception: pass` with no logging when canonical resolver crashes.

### Test Gaps

16. **[test-analyzer] `check-workspace-scope.py` zero test coverage** — Write-isolation enforcement hook (security boundary) with deny paths, JSON parsing, and progressive narrowing all untested.

17. **[test-analyzer] `check-mcp-health.py` zero test coverage** — Complex circuit-breaker with two-tier checks, file locking, and three-way return values.

### Type Design

18. **[type-analyzer] Workflow state dict construction duplicated** — `track-workflow-skill.py:74-79` bypasses `set_active_workflow()` with inline dict construction + hand-rolled YAML fallback. Schema changes will silently diverge.

19. **[type-analyzer] MCP health state duplicated** — `observe.py:214-229` reimplements `check-mcp-health.py:30-58` without TTL checking.

20. **[type-analyzer] Build state test fixture uses different keys than production** — `test_workflow_state.py:111-115` uses `phase/targets/completed` but `render-summary.py:205-213` reads `layers/decisions`.

---

## Suggestions (nice to have)

### Simplification

21. **[simplifier] 8 files duplicate "get active workflow" pattern** — Same 6-line block in 8 hooks. Extract to `get_current_workflow_context()` helper.

22. **[simplifier] Session ID resolution in 4 places** — `hook_utils.py`, `workspace-common.sh`, `detect-ivy-workspace.sh`, `start-serena.sh` each implement differently.

23. **[simplifier] `render-summary.py:build_summary()` 107 lines combining 6 concerns** — Extract lint analysis, claim counting, tool metrics, build state, journal audit, knowledge gate into separate functions.

24. **[simplifier] `observe.py:_build_payload()` 106-line if/elif chain** — Replace with dispatch dict mapping event types to handlers.

25. **[simplifier] Shell hooks that shell out to Python** — `block-direct-ivy.sh` and `post-write-ivy-lint.sh` would be simpler as Python scripts.

26. **[simplifier] `start-ivy-server.sh` launch block duplicated** — Lines 204-228 have two copies of the same 3-way branch for lsp vs mcp modes.

### Comments

27. **[comment-analyzer] `hook_utils.py:17-19` docstring lists phantom "session file" in priority chain** — No session file lookup exists in the code.

28. **[comment-analyzer] Historical replacement references** — `render-summary.py:6` and `observe.py:5` reference deleted predecessors.

### Type Design

29. **[type-analyzer] All structured data flows as plain dicts** — No TypedDicts, dataclasses, or formal types. Adding `WorkflowState` and `JournalEntry` TypedDicts would make contracts grep-visible.

30. **[type-analyzer] Journal entry payload shapes are implicit per event type** — Seven event types with different payload keys, no documentation of which keys each type carries.

---

## Strengths

- **Test infrastructure exists**: 210 tests covering hooks, workspace detection, workflow state, manifests, observability, and documentation validation.
- **Observability pipeline**: Unified `observe.py` replaces 11 individual scripts with consistent event logging.
- **Workflow state management**: Centralized YAML-based state with journal rotation and staleness detection.
- **Centralized hook utilities**: `hook_utils.py` provides shared session ID resolution, workspace root detection, and hook output formatting.
- **Well-documented hooks**: `check-mcp-health.py` module docstring accurately describes two-tier architecture and threshold behavior.

---

## Summary

| Category | Critical | Important | Suggestion |
|----------|----------|-----------|------------|
| Security | 2 | 0 | 0 |
| Logic bugs | 3 | 2 | 0 |
| Silent failures | 2 | 4 | 0 |
| Test gaps/failures | 1 | 2 | 0 |
| Type design | 0 | 3 | 2 |
| Comments | 0 | 1 | 2 |
| Simplification | 0 | 0 | 6 |
| **Total** | **8** | **12** | **10** |

**Recommended action**: Fix the command injection (item 1), multi-session kill (item 2), JSON schema parsing (item 3), and the 8 failing tests (item 8) before merge. The `find_protocol_dir` fallback (item 4) and non-blocking contract violations (item 7) should also be addressed as they affect production reliability.
