---
name: nct-model-info
description: Display the structure of an Ivy model via ivy-tools
arguments:
  - name: file
    description: Path to the .ivy file to inspect (relative to project root)
    required: true
  - name: isolate
    description: Optional isolate name to display information about
    required: false
---

Display the model structure of the specified Ivy file using ivy-tools.

## Instructions

1. Accept the file path argument. If no file is provided, ask the user which .ivy file to inspect.

2. Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` with:
   - `relative_path`: the provided file path
   - `isolate`: the isolate argument if provided, otherwise omit

3. Parse the JSON result containing `success`, `output`, and `duration_seconds`.

4. Present the model structure in a readable format:

```
## Model Structure: {file_path}

**Isolate:** {isolate or "all"}

### Types
{List all type definitions from the output}

### Relations
{List all relation definitions}

### Functions
{List all function definitions}

### Actions
{List all action definitions with their signatures}

### Invariants
{List all invariant definitions}

### Isolates
{List all isolate definitions}
```

5. If the output is large, organize it into collapsible sections or summarize with key counts:
   - "X types, Y relations, Z actions, W invariants"

6. If success is false, present the error and suggest using `/nct-check` to diagnose.

**IMPORTANT**: Do NOT run `ivy_show` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info`.
