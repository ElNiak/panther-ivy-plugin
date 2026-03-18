#!/usr/bin/env bash
# Launch the Ivy LSP server, preferring local submodule source when available.
#
# Detection priority:
#   1. IVY_LSP_DEV_ROOT env var (explicit override)
#   2. Local submodule at panther_ivy/submodules/ivy-lsp/
#   3. Fallback: GitHub package (remote)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=workspace-common.sh
source "$SCRIPT_DIR/workspace-common.sh"

_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"

log() {
    echo "[ivy-lsp] $*" >>"$LOG_FILE"
}

# --- Resolve ivy-lsp source ---

detect_ivy_workspace
resolve_ivy_lsp_source

# --- Launch ---

REINSTALL_FLAG=""
if [ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ]; then
    REINSTALL_FLAG="--reinstall"
fi

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using local ivy-lsp source: $IVY_LSP_SRC"
    # shellcheck disable=SC2086
    exec uvx \
        $REINSTALL_FLAG \
        --from "$IVY_LSP_SRC" \
        --with z3-solver \
        ivy_lsp \
        2>>"$LOG_FILE"
else
    log "Using remote ivy-lsp source"
    exec uvx \
        --from "git+https://github.com/ElNiak/ivy-lsp" \
        --with z3-solver \
        ivy_lsp \
        2>>"$LOG_FILE"
fi
