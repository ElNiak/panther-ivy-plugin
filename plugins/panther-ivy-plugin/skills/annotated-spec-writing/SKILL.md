---
name: Annotated Spec Writing
description: This skill should be used when the user asks about "writing annotated specs", "bracket tags", "RFC traceability annotations", "tagged assertions", "requirement coverage", "annotating Ivy files", or mentions adding RFC bracket tag annotations to Ivy specifications for traceability in the PANTHER framework.
---

# Writing Annotated Ivy Specifications

## Overview

Annotated specifications link formal Ivy assertions to RFC requirements using bracket tag comments. This enables automated traceability, coverage tracking, and gap analysis through the Ivy LSP semantic model.

## Bracket Tag Syntax

Every `require`, `ensure`, `assume`, or `assert` statement should include a bracket tag comment:

```ivy
# Single tag
require conn_state = open;  # [rfc9000:4.1]

# Multiple tags (comma-separated)
require pkt.size <= max_packet_size;  # [rfc9000:14.1, rfc9000:8.1]

# Tag format: [rfc{number}:{section}]
ensure stream_data_delivered;  # [rfc9000:2.2]
```

## Tag ID Convention

| Component | Format | Example |
|---|---|---|
| RFC number | `rfc` + number (no space) | `rfc9000` |
| Section | colon + section number | `:4.1` |
| Sub-section | dot-separated | `:4.1.2` |
| Full tag | `rfc{N}:{S}` | `rfc9000:4.1` |

## Workflow for Writing Annotated Specs

### Step 1: Identify Requirements
Before writing assertions, consult:
- The RFC text for the protocol section you're implementing
- The `*_requirements.yaml` manifest (if available)
- Use `ivy_extract_requirements` MCP tool to parse RFC text

### Step 2: Write Assertions with Tags
For each monitor block (`before`/`after`/`around`):

```ivy
before send_packet(src: endpoint, dst: endpoint, pkt: packet) {
    # Frame validation
    require pkt.frame_type != 0;  # [rfc9000:12.4]

    # Connection state
    require conn_state(src, dst) = open;  # [rfc9000:5.1]

    # Size limit
    require pkt.payload_length <= max_datagram_size;  # [rfc9000:14.1]
}
```

### Step 3: Check Coverage
After writing, verify coverage using:
- `ivy_requirement_coverage` MCP tool for statistics
- `ivy_traceability_matrix` MCP tool for the full mapping
- The LSP code lens at line 0 shows per-RFC coverage summary

### Step 4: Review Diagnostics
The Ivy LSP provides real-time feedback:
- **Hint** (blue): Assertion without bracket tag — add a tag
- **Warning** (yellow): Orphaned tag — tag doesn't match any manifest entry
- **Code Lens**: RFC tag overlay showing `[rfc9000:4.1] (MUST)` on annotated lines

## Requirement Manifest

Create `{rfc}_requirements.yaml` files to enable full traceability:

```yaml
rfc: "RFC9000"
requirements:
  rfc9000:4.1:
    text: "A sender MUST NOT send data on a stream beyond the current limit"
    section: "4.1"
    level: MUST
    layer: stream
    testable: true
```

The manifest enables:
- Orphaned tag detection (tags not in manifest)
- Coverage statistics by level (MUST/SHOULD/MAY)
- Coverage statistics by layer (frame/packet/connection)
- Prioritized gap analysis

## Best Practices

1. **Tag every assertion** — Even trivial ones, for complete traceability
2. **One requirement per tag** — Don't combine unrelated requirements
3. **Use multi-tags sparingly** — Only when an assertion genuinely covers multiple requirements
4. **Keep manifests updated** — When you discover new requirements, add them
5. **Review orphaned tags** — They indicate manifest-spec drift
6. **Level matters** — MUST requirements should be covered first, SHOULD second
