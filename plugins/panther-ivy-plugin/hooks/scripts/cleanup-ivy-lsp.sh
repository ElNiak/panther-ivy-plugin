#!/usr/bin/env bash
# Kill ivy_lsp processes that are children of uvx (stale MCP sessions).
# Uses SIGTERM for graceful shutdown.
pkill -TERM -f "ivy_lsp.*--mcp" 2>/dev/null || true
