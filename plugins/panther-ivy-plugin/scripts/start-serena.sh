#!/usr/bin/env bash
# Launch Serena MCP server with Ivy language support.
#
# Usage: start-serena.sh
#
# Reuses workspace-common.sh for workspace detection and ivy-lsp resolution.
# Ensures ivy_lsp is on PATH (required by Serena's IvyLanguageServer).
set -euo pipefail

# Serena is optional — disabled by default.
# Set PANTHER_IVY_ENABLE_SERENA=1 in your environment to enable.
if [ "${PANTHER_IVY_ENABLE_SERENA:-0}" = "0" ]; then
    echo "[serena] Disabled (PANTHER_IVY_ENABLE_SERENA != 1). Set to 1 to enable." >&2
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=workspace-common.sh
source "$SCRIPT_DIR/workspace-common.sh"

# --- Log setup ---
_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${_LOG_DIR}/serena-${_LOG_TS}-$$.log"

log() { echo "[serena] $*" >>"$LOG_FILE"; }

# --- Workspace detection ---
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

log "Detected workspace: $DETECTED_ROOT (type=$DETECTED_TYPE)"
export IVY_WORKSPACE_ROOT="$DETECTED_ROOT"

# --- Env vars for IvyLanguageServer ---
if [ "$DETECTED_TYPE" = "panther" ]; then
    if [ ! -f "$DETECTED_ROOT/.ivyworkspace" ]; then
        export IVY_LSP_INCLUDE_PATHS="${IVY_LSP_INCLUDE_PATHS:-protocol-testing}"
        export IVY_LSP_EXCLUDE_PATHS="${IVY_LSP_EXCLUDE_PATHS:-submodules,test,doc,examples,notebooks,patches,ivy}"
    fi
fi

# --- Resolve ivy-lsp source and ensure ivy_lsp is on PATH ---
resolve_ivy_lsp_source

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
else
    log "No local ivy-lsp found — ivy_lsp must already be on PATH"
fi

# --- Resolve panther-serena source ---
SERENA_SRC=""
if [ -n "${panther_ivy_dir:-}" ]; then
    candidate="$panther_ivy_dir/submodules/panther-serena"
    if [ -d "$candidate/src/serena" ]; then
        SERENA_SRC="$candidate"
    fi
fi

if [ -z "$SERENA_SRC" ]; then
    # Walk up looking for panther-serena
    check="$PWD"
    depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        candidate="$check/panther/plugins/services/testers/panther_ivy/submodules/panther-serena"
        if [ -d "$candidate/src/serena" ]; then
            SERENA_SRC="$candidate"
            break
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
fi

if [ -z "$SERENA_SRC" ]; then
    log "ERROR: panther-serena not found"
    echo "Error: panther-serena source not found" >&2
    exit 1
fi

log "Using panther-serena: $SERENA_SRC"

# --- Resolve serena-mcp-server binary ---
SERENA_BIN=""
SERENA_VENV="$SERENA_SRC/.venv"

# 1. Pre-built .venv (most reliable, sandbox-safe)
if [ -x "$SERENA_VENV/bin/serena-mcp-server" ]; then
    SERENA_BIN="$SERENA_VENV/bin/serena-mcp-server"
    log "Using pre-built .venv: $SERENA_BIN"
# 2. Already on PATH
elif command -v serena-mcp-server &>/dev/null; then
    SERENA_BIN="$(command -v serena-mcp-server)"
    log "Using PATH: $SERENA_BIN"
# 3. Try uv sync to populate .venv
else
    log "serena-mcp-server not found, trying uv sync..."
    if uv sync --project "$SERENA_SRC" 2>>"$LOG_FILE"; then
        if [ -x "$SERENA_VENV/bin/serena-mcp-server" ]; then
            SERENA_BIN="$SERENA_VENV/bin/serena-mcp-server"
            log "uv sync succeeded: $SERENA_BIN"
        fi
    fi
fi

if [ -z "$SERENA_BIN" ]; then
    echo "ERROR: serena-mcp-server not found. Run: cd $SERENA_SRC && uv sync" >&2
    exit 1
fi

# Verify ivy_lsp is available (required by Serena's IvyLanguageServer)
if ! command -v ivy_lsp &>/dev/null && [ ! -x "$SERENA_VENV/bin/ivy_lsp" ]; then
    echo "ERROR: ivy_lsp not found. Serena requires ivy_lsp on PATH." >&2
    echo "Fix: cd $SERENA_SRC && uv sync" >&2
    exit 1
fi

# Ensure ivy_lsp is on PATH (Serena's IvyLanguageServer calls shutil.which("ivy_lsp"))
export PATH="$SERENA_VENV/bin:$PATH"

# --- Session ID propagation ---
if [ -z "${IVY_SESSION_ID:-}" ]; then
    if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
        export IVY_SESSION_ID="$CLAUDE_SESSION_ID"
    elif [ -n "${CLAUDE_CODE_SESSION_ID:-}" ]; then
        export IVY_SESSION_ID="$CLAUDE_CODE_SESSION_ID"
    fi
fi

# --- Launch Serena MCP server ---
log "Launching serena-mcp-server with project root: $DETECTED_ROOT"
# Ensure serena + ivy-lsp are importable regardless of .pth file state (uv sync race)
export PYTHONPATH="$SERENA_SRC/src:${IVY_LSP_SRC:+$IVY_LSP_SRC:}${PYTHONPATH:-}"
exec "$SERENA_BIN" --project "$DETECTED_ROOT" --context claude-code 2>>"$LOG_FILE"
