#!/usr/bin/env bash
# One-shot rename of .panther-ivy/build-state.yaml -> scaffold-state.yaml
# across protocol-testing/<protocol>/ directories.
#
# Pairs with the workflow_state.py rename in C1 (Phase 2.1):
#   _BUILD_STATE_FILE -> _SCAFFOLD_STATE_FILE
#   get/set/get_safe build_state -> scaffold_state symbols
#   BuildStateParseError -> ScaffoldStateParseError
#
# Per feedback_no_backward_compat_shims: this script is deletable after first
# run. Idempotent: skips files where the new name already exists; warns and
# continues. Aborts on missing source dirs rather than silently doing nothing.
#
# Usage:
#   bash scripts/migrate-build-state.sh                      # default protocol-testing/
#   bash scripts/migrate-build-state.sh path/to/proto-root   # custom root
set -euo pipefail

PROTOCOL_ROOT="${1:-protocol-testing}"

if [[ ! -d "$PROTOCOL_ROOT" ]]; then
    echo "ERROR: protocol root not found: $PROTOCOL_ROOT" >&2
    exit 1
fi

renamed=0
skipped=0
shopt -s nullglob
for old in "$PROTOCOL_ROOT"/*/.panther-ivy/build-state.yaml; do
    new="${old%/build-state.yaml}/scaffold-state.yaml"
    if [[ -e "$new" ]]; then
        echo "WARN: $new already exists; skipping $old" >&2
        skipped=$((skipped + 1))
        continue
    fi
    if git ls-files --error-unmatch "$old" >/dev/null 2>&1; then
        git mv "$old" "$new"
    else
        mv "$old" "$new"
    fi
    echo "renamed: $old -> $new"
    renamed=$((renamed + 1))
done

echo
echo "summary: $renamed renamed, $skipped skipped"
