#!/usr/bin/env bash
# Launch Ivy LSP, preferring local source when available.
# Priority: IVY_LSP_DEV_ROOT env var > local submodule > GitHub remote
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON="$SCRIPT_DIR/../panther-ivy-plugin/scripts/workspace-common.sh"

_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-lsp-latest.log"
log() { echo "[ivy-lsp] $*" >>"$LOG_FILE"; }

if [ -f "$COMMON" ]; then
    source "$COMMON"
    detect_ivy_workspace
    resolve_ivy_lsp_source
else
    log "workspace-common.sh not found at $COMMON, using remote"
    IVY_LSP_SRC=""
fi

REINSTALL_FLAG=""
[ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ] && REINSTALL_FLAG="--reinstall"

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
    # shellcheck disable=SC2086
    exec uvx $REINSTALL_FLAG --from "$IVY_LSP_SRC" --with z3-solver ivy_lsp 2>>"$LOG_FILE"
else
    log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
    exec uvx --from "git+https://github.com/ElNiak/ivy-lsp" --with z3-solver ivy_lsp 2>>"$LOG_FILE"
fi
