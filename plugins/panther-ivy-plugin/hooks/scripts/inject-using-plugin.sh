#!/bin/bash
# inject-using-plugin.sh — SessionStart hook for panther-ivy-plugin
#
# Emits the body of skills/meta-using-panther-ivy-plugin/SKILL.md as
# `additionalContext` wrapped in <EXTREMELY_IMPORTANT> markers, so Claude
# loads the 1% rule, iron-law primer, methodology routing, and workspace
# awareness primer at the start of every session.
#
# Failure mode: if the SKILL.md file is missing or unreadable, exit 0
# silently. SessionStart hooks must NOT block session start; the priority
# overview is best-effort.

set -euo pipefail

SKILL_FILE="${CLAUDE_PLUGIN_ROOT}/skills/meta-using-panther-ivy-plugin/SKILL.md"

if [ ! -r "$SKILL_FILE" ]; then
  exit 0
fi

python3 - "$SKILL_FILE" <<'PY'
import json
import sys

skill_path = sys.argv[1]
try:
    with open(skill_path) as fh:
        content = fh.read()
except OSError:
    sys.exit(0)

# Strip YAML frontmatter: split on first two `---` lines, keep the body.
parts = content.split('---', 2)
body = parts[2].strip() if len(parts) >= 3 else content.strip()

wrapped = (
    "<EXTREMELY_IMPORTANT>\n"
    "panther-ivy-plugin priority overview (loaded at SessionStart)\n\n"
    f"{body}\n"
    "</EXTREMELY_IMPORTANT>"
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": wrapped
    }
}))
PY
