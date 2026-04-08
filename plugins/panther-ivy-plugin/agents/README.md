# Agents

## Overview

This directory contains 3 internal-only agents dispatched by workflow skills. They are not invoked directly by users.

| Agent | Dispatched By | Purpose |
|-------|---------------|---------|
| spec-analyst | verify, navigate | Navigate specs, verify, compile, diagnose failures |
| model-reviewer | review, verify | Review Ivy model quality, structural and type safety audit |
| traceability-agent | review, build | Extract RFC requirements, audit coverage, traceability gaps |

## Agent Details

### spec-analyst

**Purpose:** Specification navigator, verifier, and diagnostician. Handles both exploration (navigate, explain, trace dependencies) and verification (formal checking, compilation, error diagnosis).

**Tools available:** `Read`, `Grep`, `Glob`, `Bash`, `Write`, `Edit`, `ToolSearch`

---

### model-reviewer

**Purpose:** Expert reviewer of Ivy formal specification models. Analyzes `.ivy` files for correctness, completeness, and adherence to best practices. Reports findings organized by severity (ERROR / WARNING / INFO). Read-only -- does not modify files.

**Tools available:** `Read`, `Grep`, `Glob`, `ToolSearch`

---

### traceability-agent

**Purpose:** RFC requirement extraction and traceability review specialist. Extracts requirements from RFC text, generates YAML manifests, and audits coverage gaps.

**Tools available:** `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `ToolSearch`
