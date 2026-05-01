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
