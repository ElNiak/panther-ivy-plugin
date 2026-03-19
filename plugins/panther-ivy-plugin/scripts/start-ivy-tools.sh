#!/usr/bin/env bash
# Backward-compatibility wrapper — delegates to the unified start-ivy-server.sh.
exec "$(dirname "$0")/start-ivy-server.sh" --mode mcp
