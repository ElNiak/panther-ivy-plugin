#!/usr/bin/env bash
# One-shot migration: rewrite .panther-ivy/active-workflow YAML files from
# the pre-Phase-C schema (workflow: workflow-verify, ...) to the post-E
# schema (workflow: verify, etc.).
#
# Idempotent: skips files already on the new schema.
# Compatible with bash 3.2+ (no associative arrays — macOS ships bash 3.2.57).
set -euo pipefail

usage() { echo "usage: $0 [--dry-run] [<protocol-testing-root>]"; exit 1; }

DRY=0
[[ "${1:-}" == "--dry-run" ]] && { DRY=1; shift; }
ROOT="${1:-protocol-testing}"

[[ -d "$ROOT" ]] || { echo "error: $ROOT not a directory" >&2; exit 1; }

# Map old workflow names to new ones (bash 3.2-compatible).
map_old_to_new() {
  case "$1" in
    workflow-navigate) echo "ivy" ;;
    workflow-build)    echo "build" ;;
    workflow-verify)   echo "verify" ;;
    workflow-review)   echo "review" ;;
    workflow-triage)   echo "triage" ;;
    *)                 echo "" ;;
  esac
}

migrated=0
skipped=0
for f in "$ROOT"/*/.panther-ivy/active-workflow; do
  [[ -f "$f" ]] || continue
  current=$(grep -E '^workflow: ' "$f" | head -1 | awk '{print $2}')
  if [[ -z "$current" ]]; then
    skipped=$((skipped+1))
    continue
  fi
  new=$(map_old_to_new "$current")
  if [[ -n "$new" ]]; then
    if [[ $DRY -eq 1 ]]; then
      echo "[DRY] $f: $current → $new"
    else
      sed -i '' "s/^workflow: $current$/workflow: $new/" "$f"
      echo "$f: $current → $new"
    fi
    migrated=$((migrated+1))
  else
    skipped=$((skipped+1))  # already on new schema or unknown name
  fi
done

echo "Migration complete: $migrated migrated, $skipped skipped."
