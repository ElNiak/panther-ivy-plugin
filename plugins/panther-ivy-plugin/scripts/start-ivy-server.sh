#!/usr/bin/env bash
# Unified Ivy server launcher for both LSP and MCP modes.
#
# Usage:
#   start-ivy-server.sh --mode lsp        # Language Server Protocol (stdio)
#   start-ivy-server.sh --mode mcp        # Model Context Protocol (stdio, standalone)
#   start-ivy-server.sh --mode mcp-bridge # stdio↔HTTP bridge to LSP sidecar
#
# All modes share workspace detection, ivy-lsp source resolution, PID tracking,
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

if [[ "$MODE" != "lsp" && "$MODE" != "mcp" && "$MODE" != "mcp-bridge" ]]; then
    echo "Usage: $0 --mode lsp|mcp|mcp-bridge" >&2
    exit 1
fi

# Deprecation notice: MCP is now served by the unified LSP process via HTTP sidecar.
# Standalone --mode mcp is kept for backward compatibility and CI usage.
if [ "$MODE" = "mcp" ]; then
    echo "[ivy-mcp] NOTE: Standalone MCP mode is deprecated. MCP tools are now" >&2
    echo "[ivy-mcp] served by the LSP process via HTTP sidecar on port \${IVY_MCP_PORT:-19847}." >&2
    echo "[ivy-mcp] This mode is kept for backward compatibility." >&2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=workspace-common.sh
source "$SCRIPT_DIR/workspace-common.sh"

# --- Log setup (separate files per mode) ---
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log}"

# Mode-specific symlinks
if [ "$MODE" = "lsp" ]; then
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-lsp-latest.log"
else
    # Both mcp and mcp-bridge share the mcp log symlink
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-mcp-latest.log"
fi

log() { echo "[ivy-${MODE}] $*" >>"$LOG_FILE"; }

# --- Workspace detection ---
detect_ivy_workspace

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
[ "$MODE" = "mcp" ] && log "Include paths: ${IVY_LSP_INCLUDE_PATHS:-<none>}"
[ "$MODE" = "mcp" ] && log "Exclude paths: ${IVY_LSP_EXCLUDE_PATHS:-<none>}"

# --- Resolve ivy-lsp source ---
resolve_ivy_lsp_source

REINSTALL_FLAG=""
[ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ] && REINSTALL_FLAG="--reinstall"

# --- mcp-bridge: wait for sidecar, then relay stdio↔HTTP ---
if [ "$MODE" = "mcp-bridge" ]; then
    _BRIDGE_WS_HASH="$(printf '%s' "$DETECTED_ROOT" | shasum -a 256 | cut -c1-12)"
    PORT_FILE="/tmp/ivy-mcp-${_BRIDGE_WS_HASH}.port"
    BRIDGE_TIMEOUT=15  # seconds

    log "Waiting for sidecar port file: $PORT_FILE (timeout=${BRIDGE_TIMEOUT}s)"
    WAITED=0
    while [ ! -f "$PORT_FILE" ] && [ "$WAITED" -lt "$((BRIDGE_TIMEOUT * 10))" ]; do
        sleep 0.1
        WAITED=$((WAITED + 1))
    done

    if [ -f "$PORT_FILE" ]; then
        MCP_PORT=$(cat "$PORT_FILE")
        log "Sidecar found on port $MCP_PORT, starting stdio↔HTTP bridge"
        if [ -n "$IVY_LSP_SRC" ]; then
            log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
            # shellcheck disable=SC2086
            exec uvx $REINSTALL_FLAG --from "${IVY_LSP_SRC}[mcp]" \
                python -m ivy_lsp.mcp_bridge "$MCP_PORT" 2>>"$LOG_FILE"
        else
            log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
            exec uvx --from "git+https://github.com/ElNiak/ivy-lsp[mcp]" \
                python -m ivy_lsp.mcp_bridge "$MCP_PORT" 2>>"$LOG_FILE"
        fi
    else
        log "Sidecar not available after ${BRIDGE_TIMEOUT}s, falling back to standalone MCP"
        MODE="mcp"  # fall through to existing mcp launch below
    fi
fi

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
    if kill -0 "$old_pid" 2>/dev/null; then
        log "Killing stale ${MODE} server for this workspace (PID=$old_pid)"
        kill -TERM "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pidfile" 2>/dev/null || true
done

# Also clean up dead PID files from ANY workspace (stale leftovers)
for pidfile in "$PID_DIR"/${MODE}-*.pid; do
    [ -f "$pidfile" ] || continue
    old_pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if ! kill -0 "$old_pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

# Use exec to replace this process with uvx, preserving stdin/stdout pipes.
# Background (&) would redirect stdin from /dev/null in non-interactive shells,
# breaking MCP/LSP stdio transport.
echo $$ > "$PID_DIR/${_PID_PREFIX}-$$.pid"
trap 'rm -f "$PID_DIR/${_PID_PREFIX}-$$.pid" 2>/dev/null' EXIT TERM INT

# --- Launch ---
if [ "$MODE" = "lsp" ]; then
    if [ -n "$IVY_LSP_SRC" ]; then
        log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
        # shellcheck disable=SC2086
        exec uvx $REINSTALL_FLAG --from "$IVY_LSP_SRC" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE"
    else
        log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
        exec uvx --from "git+https://github.com/ElNiak/ivy-lsp" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE"
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
