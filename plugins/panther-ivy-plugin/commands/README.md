# Commands

## Overview

This directory contains 7 shortcut commands for direct Ivy tool access within the panther-ivy-plugin for Claude Code. Five of them (`/nct-check`, `/nct-compile`, `/nct-model-info`, `/nct-iut-test`, `/nct-observability`) wrap ivy-tools MCP tools; `/nct-health` runs the 9-step diagnostic via the `triage` skill; `/nct-learn` manually triggers `knowledge-capture`. All commands use the `ivy-tools` MCP surface — they do NOT invoke Ivy CLI tools directly via Bash.

The plugin also exposes two workspace-scoping commands: `/set-workspace <protocol> [<roles>]` to activate a workspace (edits outside the active protocol are then blocked by the PreToolUse hook), and `/clear-workspace` to remove the restriction. Called without arguments, `/set-workspace` reports the current state and the available groups (`quic`, `apt`, `apt_quic`, `minip`, `bgp`, `coap`, `scaffolds`).

For guided multi-step operations, use the workflow skills (`verify`, `build`, `review`, `triage`, `navigate`) instead.

## Command Reference

| Command | Description | Required Args | Optional Args |
|---------|-------------|---------------|---------------|
| `/nct-check` | Run formal verification on an Ivy specification file via `ivy_verify` | `file` -- path to `.ivy` file | `isolate` -- isolate name to check |
| `/nct-compile` | Compile an Ivy model to a test binary via `ivy_compile` | `file` -- path to `.ivy` file | `target` -- compilation target (default `"test"`); `isolate` -- isolate name |
| `/nct-model-info` | Display the structure of an Ivy model via `ivy_model_info` | `file` -- path to `.ivy` file | `isolate` -- isolate name to inspect |
| `/nct-health` | Run the full 9-step diagnostic sequence for LSP + MCP integration | (none) | (none) |
| `/nct-observability` | Query and analyze Ivy observability session logs (JSONL) | (none) | `mode` -- `"summary"` (default), `"events"`, `"errors"`, `"timeline"` |

## Mode Classification

4 commands are **FAST** -- they execute immediately with no workflow activation required. `/nct-health` is **SLOW** -- it runs a 9-step, 3-phase diagnostic sequence with agent reviews.

| Command | MCP Tool |
|---------|----------|
| `/nct-check` | `ivy_verify` |
| `/nct-compile` | `ivy_compile` |
| `/nct-model-info` | `ivy_model_info` |
| `/nct-health` | Multi-tool (9-step diagnostic) |
| `/nct-observability` | (reads JSONL logs directly) |
