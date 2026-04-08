---
name: triage
description: "Stack health diagnostics and recovery — checks MCP, LSP, and Serena servers. Activated when tools are broken, on 'not working' complaints, or as a preflight before other workflows."
---

# Triage Workflow

Read `.panther-ivy/active-workflow` on every turn to determine your current phase before proceeding.

---

## Phase 1 — Quick Check

Target: under 5 seconds. Run all checks before producing any output.

### Check 1: Stale PID files

```bash
for f in /tmp/ivy-lsp-*.pid /tmp/ivy-mcp-*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f" 2>/dev/null)
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "ALIVE: $f (pid=$pid)"
  else
    echo "STALE: $f (pid=$pid)"
  fi
done
```

Record which PIDs are alive and which are stale.

### Check 2: MCP server

Call `ivy_capabilities` with no arguments. This is the fastest MCP round-trip. If it returns a tool list, MCP is alive.

### Check 3: LSP server

Look for recent diagnostics in `<new-diagnostics>` blocks from the current session. If none, check `/tmp/ivy-lsp-lsp-latest.log` for activity within the last 60 seconds:

```bash
if [ -f /tmp/ivy-lsp-lsp-latest.log ]; then
  age=$(( $(date +%s) - $(stat -f %m /tmp/ivy-lsp-lsp-latest.log) ))
  echo "LSP log age: ${age}s"
  tail -5 /tmp/ivy-lsp-lsp-latest.log
fi
```

### Check 4: Serena server (conditional)

Only check if `PANTHER_IVY_ENABLE_SERENA=1` is set:

```bash
if [ "$PANTHER_IVY_ENABLE_SERENA" = "1" ]; then
  # Check for Serena process
  pgrep -f "serena" > /dev/null 2>&1 && echo "SERENA: ALIVE" || echo "SERENA: DEAD"
fi
```

### Evaluate Results

**If everything is healthy:**

- If `invocation_depth > 0` (preflight mode): Return silently to caller. Do not produce any user-facing output. Decrement `invocation_depth` and restore the caller's workflow in the active-workflow file.
- If `invocation_depth == 0` (direct invocation): Report "Stack is healthy. MCP, LSP [, and Serena] all responding." Then clear the active-workflow flag and return to navigate.

**If something is dead:** Update phase to `"diagnose"` via `update_workflow_phase()` and proceed to Phase 2.

---

## Phase 2 — Diagnose

Only reached when Phase 1 found at least one dead component.

### Identify failures

For each dead component, check logs for the crash reason:

| Component | Log File | Common Causes |
|-----------|----------|---------------|
| MCP | `/tmp/ivy-mcp-latest.log` | Port conflict, import error, uncaught exception |
| LSP | `/tmp/ivy-lsp-lsp-latest.log` | Indexing failure, Z3 import error, workspace path issue |
| Serena | Serena's own log path | Missing `.venv`, missing submodule |

```bash
# Check for port conflicts
for f in /tmp/ivy-mcp-*.port; do
  [ -f "$f" ] || continue
  port=$(cat "$f" 2>/dev/null)
  lsof -i :"$port" 2>/dev/null | head -5
done
```

### Present diagnosis

Report to the user with specifics:

```
[Component] is down.
Reason: [extracted from log — last error line or traceback summary]
[If port conflict: "Port N is in use by another process."]
[If stale PID: "PID file exists but process is dead."]

Want me to restart it?
```

Wait for user confirmation before proceeding to Phase 3. Update phase to `"fix"` via `update_workflow_phase()`.

---

## Phase 3 — Fix

Only reached after user confirms they want a restart.

### Step 1: Clean up stale state

```bash
# Remove stale PID files for dead processes
for f in /tmp/ivy-lsp-*.pid /tmp/ivy-mcp-*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f" 2>/dev/null)
  if ! ps -p "$pid" > /dev/null 2>&1; then
    rm -f "$f"
    echo "Removed stale PID file: $f"
  fi
done

# Remove stale port files if TCP is unreachable
for f in /tmp/ivy-mcp-*.port; do
  [ -f "$f" ] || continue
  port=$(cat "$f" 2>/dev/null)
  if ! nc -z -w 2 127.0.0.1 "$port" 2>/dev/null; then
    rm -f "$f"
    echo "Removed stale port file: $f"
  fi
done
```

### Step 2: Trigger restart

Claude Code auto-restarts MCP/LSP servers on the next tool invocation. After cleaning stale files, invoke a lightweight MCP call to trigger the restart:

- For MCP: call `ivy_capabilities` — the sidecar restarts automatically
- For LSP: the next LSP-dependent operation triggers restart

### Step 3: Verify recovery

Re-run Phase 1 checks to confirm the stack is back up.

**If recovered:** Report success and proceed to completion.

**If still broken:** Escalate with a full diagnostic dump:

```
Recovery failed. Full diagnostics:
- MCP log (last 20 lines): [content]
- LSP log (last 20 lines): [content]
- PID files: [list]
- Port files: [list]
- Environment: IVY_WORKSPACE_ROOT=[value], IVY_LSP_DEV_ROOT=[value]

Suggested manual steps:
1. Check if uvx is on PATH
2. Try: kill $(cat /tmp/ivy-lsp-*.pid) then retry
3. Run /nct-health for deep 9-step diagnostics
```

---

## Preflight Export

Other workflows silently call triage Phase 1 before their first MCP tool invocation by setting `invocation_depth > 0` and `caller` to the calling workflow name.

When invoked as preflight (`invocation_depth > 0`):
- Run Phase 1 only
- On healthy: return immediately with no user interaction
- On failure: proceed to Phase 2-3 (user interaction required, since broken tools block the calling workflow)

---

## On Completion

- If `invocation_depth > 0`: Decrement depth. Restore `caller` as the active workflow in the active-workflow file. The caller resumes.
- If `invocation_depth == 0`: Clear the active-workflow flag via `clear_active_workflow()`. Navigate re-activates on the next turn.

---

## Integration

- **Called by:** `navigate` (preflight), `build`/`verify`/`review` (preflight), user directly ("things are broken")
- **Replaces:** `healthcheck` skill (deprecated — triage is the successor)
- **Related:** `/nct-health` command provides deeper 9-step diagnostics after fast triage
- **Log files:** `/tmp/ivy-lsp-lsp-latest.log`, `/tmp/ivy-mcp-latest.log`
- **PID files:** `/tmp/ivy-lsp-*.pid`, `/tmp/ivy-mcp-*.pid`
- **Port files:** `/tmp/ivy-mcp-*.port`
