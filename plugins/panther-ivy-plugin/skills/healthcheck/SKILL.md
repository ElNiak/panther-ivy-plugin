---
name: healthcheck
description: "DEPRECATED — absorbed into triage workflow. Will be removed in a future version."
---

# Ivy Stack Healthcheck

Fast, gated health triage for the Ivy MCP sidecar + LSP integration stack.

## Execution Model

Four sequential phases. Phase 1 (infrastructure) gates Phase 2 (functional) — if any Phase 1 check is CRITICAL, skip Phase 2 entirely (MCP calls on a dead sidecar just timeout).

Phase 3 (pytest) and Phase 4 (summary) always run.

## Severity Levels

| Level | Meaning |
|-------|---------|
| CRITICAL | Stack unusable — blocks all MCP tool usage |
| WARNING | Degraded — partially functional, action recommended |
| INFO | Healthy or non-blocking observation |

Track every check result as a row: `{severity, check_name, status_detail}`.

---

## Phase 1: Infrastructure Probing

Run these checks using Bash. Collect results into a findings list.

### Check 1.1 — MCP Sidecar Process Health

**What to run:**

```bash
# List PID files
ls /tmp/ivy-lsp-pids/mcp-*.pid 2>/dev/null

# For each PID file found, check if process is alive
for f in /tmp/ivy-lsp-pids/mcp-*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f" 2>/dev/null)
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "ALIVE: $f (pid=$pid)"
  else
    echo "STALE: $f (pid=$pid)"
  fi
done
```

**Severity rules:**
- No PID files found at all → **CRITICAL** — "No MCP PID files in /tmp/ivy-lsp-pids/"
- All PIDs dead (stale files only) → **CRITICAL** — "All MCP processes dead, N stale PID files"
- Some alive, some stale → **WARNING** — "N alive, M stale PID files"
- All alive → **INFO** — "N MCP processes running"

### Check 1.2 — Port File Consistency

**What to run:**

```bash
# List port files with age
ls -la /tmp/ivy-mcp-*.port 2>/dev/null

# For each port file, read port and test TCP
for f in /tmp/ivy-mcp-*.port; do
  [ -f "$f" ] || continue
  port=$(cat "$f" 2>/dev/null)
  age=$(( $(date +%s) - $(stat -f %m "$f") ))
  echo "PORT_FILE: $f port=$port age=${age}s"

  # TCP connect test (2s timeout)
  if nc -z -w 2 127.0.0.1 "$port" 2>/dev/null; then
    echo "TCP: OK on port $port"
  else
    echo "TCP: FAILED on port $port"
  fi
done
```

**Severity rules:**
- No port file found → **CRITICAL** — "No MCP port files in /tmp/"
- Port file exists but TCP connect fails → **CRITICAL** — "Port file exists (port=N) but TCP unreachable"
- Port file age > 120s but TCP works → **WARNING** — "Port file stale (Ns old) but TCP responds"
- Workspace hash in filename doesn't match current workspace → **WARNING** — "Port file workspace hash mismatch"
- Port file fresh + TCP works + hash matches → **INFO** — "MCP sidecar reachable on port N"

Note: workspace hash cross-validation is deferred until after Check 1.3 determines the `.ivyworkspace` location. Record the port file hash from the filename now and compare after Check 1.3 completes.

### Check 1.3 — Workspace Detection & Env Vars

**What to run:**

```bash
# Check env vars
echo "IVY_WORKSPACE_ROOT=${IVY_WORKSPACE_ROOT:-<unset>}"
echo "IVY_LSP_DEV_ROOT=${IVY_LSP_DEV_ROOT:-<unset>}"
echo "IVY_MCP_PORT=${IVY_MCP_PORT:-<unset>}"
echo "PANTHER_IVY_ENABLE_SERENA=${PANTHER_IVY_ENABLE_SERENA:-<unset>}"

# Check .ivyworkspace existence
# Search from workspace root or current protocol dir
find . -maxdepth 5 -name ".ivyworkspace" -type f 2>/dev/null | head -5

# If IVY_LSP_DEV_ROOT is set, verify it exists
if [ -n "$IVY_LSP_DEV_ROOT" ]; then
  [ -d "$IVY_LSP_DEV_ROOT" ] && echo "DEV_ROOT: exists" || echo "DEV_ROOT: MISSING"
fi
```

**Severity rules:**
- `IVY_LSP_DEV_ROOT` set but path doesn't exist → **WARNING** — "IVY_LSP_DEV_ROOT points to missing path: X"
- No `.ivyworkspace` found in workspace → **WARNING** — "No .ivyworkspace marker found"
- All vars consistent, marker found → **INFO** — "Workspace detection OK"

### Phase 1 Gate

Count CRITICAL findings from Checks 1.1–1.3.

**If any CRITICAL:** Report them immediately, then print:
```
Phase 2 (Functional Validation) SKIPPED — infrastructure not reachable.
Proceeding to Phase 3 (pytest) and Phase 4 (summary).
```
Skip to Phase 3.

**If no CRITICAL:** Proceed to Phase 2.

---

## Phase 2: Functional Validation

Run these checks using MCP tool calls. Only executes if Phase 1 had zero CRITICALs.

### Check 2.1 — Indexer Readiness

**What to call:**

Call the `ivy_health_check` MCP tool with no arguments.

**Parse the response for the `model_status` object, then read its `state` field.**

**Severity rules:**
- Tool call fails or times out → **CRITICAL** — "ivy_health_check unreachable"
- `model_status.state` is `"not_built"` → **CRITICAL** — "Model not built, indexing never started"
- `model_status.state` is `"failed"` → **CRITICAL** — "Model build failed"
- `model_status.state` is `"building"` → **WARNING** — "Model still building, some tools unavailable"
- `model_status.state` is `"ready"` → **INFO** — "Model ready"

### Check 2.2 — MCP Tool Smoke Tests

**What to call:**

1. Call `ivy_capabilities` with no arguments. Validate response contains keys: `cli_tools`, `mcp_tools`, `mcp_tool_count`, `staging_health`.

2. Call `ivy_workspace` with no arguments. Validate returned `workspace_root` matches expected workspace path.

**Severity rules:**
- Both calls fail or return empty → **CRITICAL** — "MCP tools unresponsive"
- One call fails or returns empty/malformed → **WARNING** — "Partial MCP tool failure: <which tool>"
- Both return valid structured data → **INFO** — "MCP tools responding (N tools registered)"

### Check 2.3 — Staging Health

**What to parse:**

From the `ivy_capabilities` response obtained in Check 2.2, extract the `staging_health` object.

**Severity rules:**
- If `ivy_capabilities` response unavailable from Check 2.2 → **WARNING** — "Staging health unknown (capabilities unavailable)"
- `symlink_failures > 0` → **WARNING** — "N symlink failures in layer staging"
- `layer_count` doesn't match `.ivyworkspace` layer count → **WARNING** — "Layer count mismatch: staging=N, config=M"
- All staging healthy → **INFO** — "Layer staging healthy (N layers, 0 failures)"

---

## Phase 3: Test Suite

Always runs regardless of earlier phases.

**Precondition:** Run from the PANTHER repository root (the worktree root).

**What to run:**

```bash
# Run ivy-lsp tests (fail-fast, quiet output)
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/ -x -q --tb=short 2>&1 | tail -20
```

**Parse the last line for pass/fail/error counts** (pytest summary line format: `N passed, M failed, K errors`).

**Severity rules:**
- >10% failure rate → **CRITICAL** — "Test suite failing: N/M tests passed (X%)"
- Any failures but ≤10% → **WARNING** — "N test failures out of M total"
- All pass → **INFO** — "All N tests passed"
- pytest itself fails to run → **WARNING** — "pytest execution error (check venv activation)"

---

## Phase 4: Summary Report

Always runs. Produce a table sorted by severity (CRITICAL first, then WARNING, then INFO):

```
| Severity | Check                        | Status                          |
|----------|------------------------------|---------------------------------|
| CRITICAL | Sidecar process (1.1)        | All processes dead              |
| WARNING  | Port file age (1.2)          | Stale (145s) but TCP responds   |
| INFO     | Workspace env vars (1.3)     | OK                              |
| SKIPPED  | Indexer readiness (2.1)      | Phase 2 skipped (infra down)    |
| ...      | ...                          | ...                             |

Overall: X CRITICAL, Y WARNING, Z INFO
Phases executed: 1, 3, 4 (Phase 2 skipped: sidecar not reachable)
```

If any CRITICAL findings exist, suggest next steps:
- "Run `/nct-health` for deep diagnostics"
- Specific remediation per finding (e.g., "Restart LSP server", "Clean stale PID files in /tmp/ivy-lsp-pids/")

---

## Integration

- **Complements:** `/nct-health` command — use `/nct-health` for deep 9-step diagnostics after fast triage
- **Uses data from:** `check-mcp-health.py` hook (same PID/port file paths)
- **Related tools:** `ivy_health_check`, `ivy_capabilities`, `ivy_workspace` MCP tools
