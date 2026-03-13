#!/usr/bin/env bash
# Launch the Ivy LSP server, preferring local submodule source when available.
#
# Detection priority:
#   1. IVY_LSP_DEV_ROOT env var (explicit override)
#   2. Local submodule at panther_ivy/submodules/ivy-lsp/
#   3. Fallback: GitHub package (remote)
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"

log() {
    echo "[ivy-lsp] $*" >>"$LOG_FILE"
}

# --- Resolve ivy-lsp source ---

IVY_LSP_SRC=""

# 1. Explicit dev root
if [ -n "${IVY_LSP_DEV_ROOT:-}" ] && [ -d "$IVY_LSP_DEV_ROOT/ivy_lsp" ]; then
    IVY_LSP_SRC="$IVY_LSP_DEV_ROOT"
fi

# 2. Walk up from CWD looking for panther_ivy/submodules/ivy-lsp/
if [ -z "$IVY_LSP_SRC" ]; then
    check="$PWD"
    depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        candidate="$check/panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp"
        if [ -d "$candidate/ivy_lsp" ]; then
            IVY_LSP_SRC="$candidate"
            break
        fi
        # Maybe CWD is inside panther_ivy
        candidate="$check/submodules/ivy-lsp"
        if [ -d "$candidate/ivy_lsp" ]; then
            IVY_LSP_SRC="$candidate"
            break
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
fi

# --- Launch ---

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using local ivy-lsp source: $IVY_LSP_SRC"
    exec uvx \
        --reinstall \
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
