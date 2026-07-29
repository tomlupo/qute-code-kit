<!-- prose source: shipping v2 — /setup-qute-repo step 5a writes this as a section of the repo's CLAUDE.md, and ONLY when the confirmed shipping mode is not `none` (a `none` repo gets the one-line alternative instead, so nothing here may hedge on that case). It is prose, not a file to copy: nothing stamps it into .claude/rules (ADR-0005 §5 as amended 2026-07-28). -->
# Shipping

- `/ship` is the **only** version writer: it bumps the version, regenerates
  `CHANGELOG.md` from Conventional Commits, refreshes the lockfile, and creates
  the annotated `vX.Y.Z` tag. Never bump versions or edit the changelog by
  hand, never hand-cut a release tag, and never add a CI workflow that bumps
  versions.
- **The branch you are on selects what `/ship` does** (ADR-0008). You do not
  choose it with a flag and you cannot forget to:

  | Where you are | What `/ship` does |
  |---|---|
  | integration branch (`dev`) | bump + changelog + lockfile + commit — **no tag** |
  | release branch (`main`), two-stage repo | `/ship --tag` creates and **pushes** the release tag |
  | release branch, single-stage repo | bump and tag in one act |
  | any other branch | **refuses**, writing nothing |

  A two-stage release is therefore two commands: bump on the integration
  branch, merge the release PR, then `/ship --tag` on the release branch. The
  first command reports the second.
- The tag is cut **after** the merge, on the release branch, so it names a
  commit that branch actually contains. That is what makes squash-merging a
  release PR safe — a tag cut before the merge points at code the release
  branch never receives.
- Release from a clean tree, after tests pass.
- **A bump in flight blocks the next one.** If the declared version has no tag,
  `/ship` refuses rather than computing the next increment off a stale
  baseline. Finish the release (`/ship --tag`) or revert the bump commit.
