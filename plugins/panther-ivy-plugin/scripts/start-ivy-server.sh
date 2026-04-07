#!/usr/bin/env bash
# Unified Ivy server launcher for both LSP and MCP modes.
#
# Usage:
#   start-ivy-server.sh --mode lsp        # Language Server Protocol (stdio)
#   start-ivy-server.sh --mode mcp        # Model Context Protocol (stdio, standalone)
#
# Both modes share workspace detection, ivy-lsp source resolution, PID tracking,
# and log setup. They differ in launch flags and workspace configuration.
set -euo pipefail

# --- Parse arguments ---
MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ "$MODE" != "lsp" && "$MODE" != "mcp" ]]; then
    echo "Usage: $0 --mode lsp|mcp" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=workspace-common.sh
source "$SCRIPT_DIR/workspace-common.sh"

# --- Log setup (initial — may be re-routed after session detection) ---
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log}"

log() { echo "[ivy-${MODE}] $*" >>"$LOG_FILE"; }

# --- Workspace detection ---
# Use IVY_WORKSPACE_ROOT from SessionStart hook if available (avoids re-detection)
if [ -n "${IVY_WORKSPACE_ROOT:-}" ] && [ -d "$IVY_WORKSPACE_ROOT" ]; then
    DETECTED_ROOT="$IVY_WORKSPACE_ROOT"
    if [ -d "$DETECTED_ROOT/protocol-testing" ]; then
        DETECTED_TYPE="panther"
        panther_ivy_dir="$DETECTED_ROOT"
    else
        DETECTED_TYPE="standalone"
    fi
else
    detect_ivy_workspace
fi

if [ "$MODE" = "mcp" ]; then
    # MCP needs include/exclude paths for workspace scoping
    if [ "$DETECTED_TYPE" = "panther" ]; then
        if [ -f "$DETECTED_ROOT/.ivyworkspace" ]; then
            log "Found .ivyworkspace — deferring path config to Python marker detection"
        else
            export IVY_LSP_INCLUDE_PATHS="${IVY_LSP_INCLUDE_PATHS:-protocol-testing}"
            export IVY_LSP_EXCLUDE_PATHS="${IVY_LSP_EXCLUDE_PATHS:-submodules,test,doc,examples,notebooks,patches,ivy}"
        fi
    fi
fi

log "Detected workspace: $DETECTED_ROOT (type=$DETECTED_TYPE)"
export IVY_WORKSPACE_ROOT="$DETECTED_ROOT"
# Ensure the Python detection (Step 1) uses the bash-detected root for both
# MCP and LSP modes.  Without this, LSP mode falls through to git-worktree
# heuristics that can resolve to the wrong worktree sibling.
export IVY_LSP_WORKSPACE="$DETECTED_ROOT"
[ "$MODE" = "mcp" ] && log "Include paths: ${IVY_LSP_INCLUDE_PATHS:-<none>}"
[ "$MODE" = "mcp" ] && log "Exclude paths: ${IVY_LSP_EXCLUDE_PATHS:-<none>}"

# Ensure IVY_SESSION_ID tracks the Claude session id.
# Delegates to resolve_session_id() from workspace-common.sh (which tries
# the canonical ivy-lsp Python resolver first, then a bash fallback).
if [ -z "${IVY_SESSION_ID:-}" ]; then
    IVY_SESSION_ID="$(resolve_session_id)"
    export IVY_SESSION_ID
fi

if [ -n "${IVY_SESSION_ID:-}" ]; then
    log "Session id resolved: ${IVY_SESSION_ID}"
else
    log "Session id unresolved; IVY_SESSION_ID is empty"
fi

# --- Session-aware log redirection ---
if [ -n "${IVY_SESSION_ID:-}" ] && [ -n "${IVY_WORKSPACE_ROOT:-}" ]; then
    SESSION_LOG_DIR="${IVY_WORKSPACE_ROOT}/.observability/sessions/${IVY_SESSION_ID}"
    mkdir -p "$SESSION_LOG_DIR"

    LOG_FILE="${SESSION_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log"
    export IVY_LSP_LOG_FILE="$LOG_FILE"
    export IVY_LSP_DEBUG_LOG_PATH="${SESSION_LOG_DIR}/debug-trace.log"

    log "Log files redirected to session dir: $SESSION_LOG_DIR"
fi

# Mode-specific symlinks (backward compat — always point to current log file)
if [ "$MODE" = "lsp" ]; then
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-lsp-latest.log"
else
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-mcp-latest.log"
fi

# --- Resolve ivy-lsp source ---
resolve_ivy_lsp_source

REINSTALL_FLAG=""
[ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ] && REINSTALL_FLAG="--reinstall"

# --- PID tracking for cleanup ---
PID_DIR="/tmp/ivy-lsp-pids"
mkdir -p "$PID_DIR"

# Workspace-scoped session ID: only kill servers for the SAME workspace,
# allowing concurrent Claude sessions on different worktrees.
_WS_HASH="$(printf '%s' "$DETECTED_ROOT" | shasum -a 256 | cut -c1-12)"
_PID_PREFIX="${MODE}-${_WS_HASH}"

# Kill stale servers of the same mode AND workspace from previous sessions
for pidfile in "$PID_DIR"/${_PID_PREFIX}-*.pid; do
    [ -f "$pidfile" ] || continue
    old_pid="$(cat "$pidfile" 2>/dev/null)" || continue
    [ "$old_pid" = "$$" ] && continue
    if ps -p "$old_pid" > /dev/null 2>&1; then
        log "Killing stale ${MODE} server for this workspace (PID=$old_pid)"
        kill -TERM "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pidfile" 2>/dev/null || true
done

# Also clean up dead PID files from ANY workspace (stale leftovers)
for pidfile in "$PID_DIR"/${MODE}-*.pid; do
    [ -f "$pidfile" ] || continue
    old_pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if ! ps -p "$old_pid" > /dev/null 2>&1; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

# Use exec to replace this process with uvx, preserving stdin/stdout pipes.
# Background (&) would redirect stdin from /dev/null in non-interactive shells,
# breaking MCP/LSP stdio transport.
echo $$ > "$PID_DIR/${_PID_PREFIX}-$$.pid"
export IVY_PID_FILE="$PID_DIR/${_PID_PREFIX}-$$.pid"
trap 'rm -f "$IVY_PID_FILE" 2>/dev/null' EXIT TERM INT

# --- Launch ---
if [ "$MODE" = "lsp" ]; then
    # Include mcp + uvicorn so the MCP HTTP sidecar can start alongside the LSP.
    if [ -n "$IVY_LSP_SRC" ]; then
        log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
        # shellcheck disable=SC2086
        exec uvx $REINSTALL_FLAG --from "${IVY_LSP_SRC}[mcp]" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE"
    else
        log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
        exec uvx --from "git+https://github.com/ElNiak/ivy-lsp[mcp]" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE"
    fi
else
    if [ -n "$IVY_LSP_SRC" ]; then
        log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
        # shellcheck disable=SC2086
        exec uvx $REINSTALL_FLAG --from "${IVY_LSP_SRC}[mcp]" ivy_lsp --mcp --workspace "$DETECTED_ROOT" 2>>"$LOG_FILE"
    else
        log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
        exec uvx --from "git+https://github.com/ElNiak/ivy-lsp[mcp]" ivy_lsp --mcp --workspace "$DETECTED_ROOT" 2>>"$LOG_FILE"
    fi
fi
