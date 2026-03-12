#!/usr/bin/env bash
# Wrapper to capture ivy_lsp stderr to a log file
LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"
exec uvx --from "git+https://github.com/ElNiak/ivy-lsp" ivy_lsp 2>>"$LOG_FILE"
