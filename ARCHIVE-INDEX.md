# Refactor archive — 2026-04-27 (pre-simplification)

This branch is an **orphan branch** (no shared history with `main`). It exists solely to preserve `.backup/` snapshots that were removed from `main` during the plugin-simplification pass on 2026-04-27.

## How this branch was created

1. From the `fix/nct-validate-ground-truth-and-scoping-docs` working branch (commits `624612c` T1.A and `3d53955` T2.A applied), `git checkout --orphan refactor-archive/2026-04-27-pre-simplification`.
2. `git rm -rf --cached .` to un-stage everything.
3. Selectively `git add` the 16 archived snapshots and this index, then commit.
4. Switch back to the working branch and `git rm -r` the same 16 snapshots there, with a paired commit on the working branch.

## Snapshots archived (16)

All paths are relative to the submodule root.

### `.claude/.backup/` — uniformization batch (Apr 24, 2026, completed migrations)

- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-p1-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-p2-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-p3a-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-p3b-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-ph-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-pi-desc-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-pi-gates-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-pi-reliability-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-pi-safety-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/uniformize-pi-scope-2026-04-24/`
- `plugins/panther-ivy-plugin/.claude/.backup/xml-restructure-2026-04-24/`

### `.claude/.backup/` — older (Apr 22–23, 2026)

- `plugins/panther-ivy-plugin/.claude/.backup/design-notes-2026-04-23/`
- `plugins/panther-ivy-plugin/.claude/.backup/rules-consolidations-2026-04-23/`
- `plugins/panther-ivy-plugin/.claude/.backup/rules-2026-04-22/`
- `plugins/panther-ivy-plugin/.claude/.backup/skills-2026-04-22/`
- `plugins/panther-ivy-plugin/.claude/.backup/workflow-audit-baseline-2026-04-23.md` *(single file)*

## Snapshots intentionally left on `main` (4)

These were judged too recent to archive (≤24 hours old at the time of T4.A):

- `plugins/panther-ivy-plugin/.backup/skills-merged-2026-04-27/`
- `plugins/panther-ivy-plugin/.backup/skills-restructure-2026-04-27/`
- `plugins/panther-ivy-plugin/.claude/.backup/superpowers-audit-2026-04-27/`
- `plugins/panther-ivy-plugin/scripts/.backup/check-xml-tags.py` *(single 8 KB file)*

## How to recover a snapshot

```bash
# From a working tree on any other branch:
git checkout refactor-archive/2026-04-27-pre-simplification -- \
  plugins/panther-ivy-plugin/.claude/.backup/<snapshot-name>
# The snapshot is now in the working tree of the current branch.
# Stage and commit (or copy the files elsewhere) as needed.
```

## Provenance

- Working branch at the time of archival: `fix/nct-validate-ground-truth-and-scoping-docs`.
- Latest working-branch commit at the time: `3d53955` (T2.A — lazy-load 4 knowledge skills).
- Plan that authorized T4.A: `~/.claude/plans/plugin-dev-plugin-structure-i-want-to-polished-wren.md`.
- T4 sub-option: `T4.A — per-snapshot AskUserQuestion` (the saved feedback rule for `.backup/` paths).

This branch should never be merged into `main`. Treat it as cold storage.
