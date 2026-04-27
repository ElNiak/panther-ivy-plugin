---
paths: ["**/*.ivy", "**/*.cpp", "**/*.h"]
---

# Propagation Authority

The `ivy_propagation(mode="impact", ...)` tool output is the single source of truth for which files to edit when propagating an Ivy type change to serializer / deserializer state machines. The `propagation-patterns` skill does not independently classify files.

Follow these rules:

- Only edit files listed in `auto_propagate`. Never edit `manual_review` or `unaffected` files.
- For each `manual_review` file, present its `reason` string to the user before proceeding.
- For hardcoded constants encountered during editing, always warn the user even if the file is in `auto_propagate`.
