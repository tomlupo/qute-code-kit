<!-- prose source: git-workflow v2 — /setup-qute-repo writes this as a CLAUDE.md section; it is NOT stamped as a .claude/rules file (TOM-386) -->
# Git workflow

- Branch off the default branch for every change; never commit directly to it
  unless the repo explicitly allows it.
- One PR per change — small, reviewable, single-purpose.
- Commit messages follow **Conventional Commits** with a scope
  (`feat(x): …`, `fix(y): …`); the release tooling parses them to pick the
  version bump.
- Keep the branch rebased/merge-clean on its base before requesting review or
  merging.
- When this repo carries `.claude/git-guard.json`, a `pre-push` hook enforces
  the two rules above at the git layer — for humans, scripts and agents alike —
  and refuses a push landing on a guarded branch. `git push --no-verify` skips
  it; that is the deliberate override, not the normal route.
