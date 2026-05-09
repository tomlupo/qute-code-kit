## v1.15.0 (2026-05-09)

### BREAKING

- **qute-essentials**: removed the `/promote` skill. Per-subsystem
  promotion ceremony with spec-frontmatter `gates:`, `LOCKED` enforcement,
  and `{alias}-vX.Y.Z` annotated tags is retired in favor of a single
  release namespace (`vX.Y.Z` set by `/ship` on `main`). Going from
  `feat/*` or `research/*` to `dev` is now a plain `gh pr create --base
  dev` (or `commit-commands:commit-push-pr`) — no ceremony, no gates,
  no per-subsystem tags. Methodology version tracking moves to the spec
  doc's frontmatter `version:` field, bumped in the same `feat/*` PR
  that lands the change. Projects that relied on `/promote` should
  update their `.claude/rules/git-workflow.md` and `methodology.md` to
  the single-namespace model. Historical `{alias}-vX.Y.Z` and
  `prod-{alias}-vX.Y.Z-YYYYMMDD` tags are preserved for archaeology;
  no new tags added in those namespaces.

## v1.14.0 (2026-05-09)

### Feat

- **qute-essentials**: /worktrees skill becomes config-driven via
  `.claude/worktree.json` (`base_path`, `branch_pattern`, `default_type`,
  `shared_dirs`, `copy_files`, `venv_setup`, `base_branch`) plus optional
  `.claude/post-worktree.sh` hook for project-specific custom setup.
  Projects with shared `data/`/`models/` dirs, custom venv layout, or
  out-of-repo worktree conventions (quant/ML monorepos) no longer need
  bespoke worktree-creation instructions in their own rules — the skill
  reads project config and applies symlinks, file copies, and uv/pip
  venv setup automatically. Worktree slug is intended to match the
  project's task-slug convention (`docs/tasks/{slug}.md`), so one
  identifier threads through branch / worktree dir / venv / Stop hook /
  handoff frontmatter. Backwards-compatible: projects without
  `worktree.json` get the prior in-repo `.worktrees/<branch>` default
  behavior.

## v1.12.0 (2026-05-01)

### Feat

- **qute-essentials**: /ship auto-wipes TASKS.md::Completed sections after
  cz bump succeeds. Work just shipped, the canonical record is in CHANGELOG.md;
  a follow-up `chore(tasks): wipe Completed after vX.Y.Z` commit lands on the
  same branch as the bump. Skipped silently if TASKS.md is missing.
- **qute-essentials**: /pickup auto-syncs local main to origin/main at the
  start of the audit (best-effort `git fetch origin main && git update-ref`).
  Prevents stale-local-main false alarms in `git tag --merged main` queries
  (the "orphan tag" misdiagnosis pattern). Skips silently on offline / no-remote.

## v1.11.0 (2026-05-01)

### Feat

- **qute-essentials**: /pickup + /promote surface stale alias-related branches.
  /pickup gains a "Stale branches" inventory bullet that scans `feat/*` and
  `research/*` refs, lists ahead/behind/age, and flags drift candidates
  (>14d stale or >20 commits behind). /promote gains a preflight scan
  (step 5) that surfaces orphan branches sharing the same alias before
  gates run, with a heuristic that picks up historical aliases from the
  Subsystems table prose. Closes the workflow gap where a LOCKED
  methodology spec sits parked on a `feat/{alias}-*` branch and gets
  left behind when a sibling release ships.
