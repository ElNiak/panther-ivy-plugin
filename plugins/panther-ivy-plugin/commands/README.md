# Commands

## Overview

This directory contains 4 shortcut commands for direct Ivy tool access within the panther-ivy-plugin for Claude Code. All commands use the `ivy-tools` MCP tools -- they do NOT invoke Ivy CLI tools directly via Bash.

For guided multi-step operations, use the workflow skills (`verify`, `build`, `review`, `triage`, `navigate`) instead.

## Command Reference

| Command | Description | Required Args | Optional Args |
|---------|-------------|---------------|---------------|
| `/nct-check` | Run formal verification on an Ivy specification file via `ivy_verify` | `file` -- path to `.ivy` file | `isolate` -- isolate name to check |
| `/nct-compile` | Compile an Ivy model to a test binary via `ivy_compile` | `file` -- path to `.ivy` file | `target` -- compilation target (default `"test"`); `isolate` -- isolate name |
| `/nct-model-info` | Display the structure of an Ivy model via `ivy_model_info` | `file` -- path to `.ivy` file | `isolate` -- isolate name to inspect |
| `/nct-observability` | Query and analyze Ivy observability session logs (JSONL) | (none) | `mode` -- `"summary"` (default), `"events"`, `"errors"`, `"timeline"` |

## Mode Classification

All 4 commands are **FAST** -- they execute immediately with no workflow activation required.

| Command | MCP Tool |
|---------|----------|
| `/nct-check` | `ivy_verify` |
| `/nct-compile` | `ivy_compile` |
| `/nct-model-info` | `ivy_model_info` |
| `/nct-observability` | (reads JSONL logs directly) |
