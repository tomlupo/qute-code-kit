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
