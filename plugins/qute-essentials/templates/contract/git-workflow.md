<!-- prose source: git-workflow v4 — /setup-qute-repo step 5 writes this as a section of the repo's CLAUDE.md. It is prose, not a file to copy: nothing stamps it into .claude/rules (ADR-0005 §5 as amended 2026-07-28). -->
# Git workflow

- Branch off the default branch for every change; never commit directly to it
  unless the repo explicitly allows it.
- One PR per change — small, reviewable, single-purpose.
- Commit messages follow **Conventional Commits** with a scope
  (`feat(x): …`, `fix(y): …`); the release tooling parses them to pick the
  version bump.
- Keep the branch rebased/merge-clean on its base before requesting review or
  merging.
- **`.claude/git-guard.json` is the opt-in.** Its *presence* — not any field in
  it — arms both guard layers for this repo; with no such file they are a total
  no-op here. Every field is optional (`{}` means the house defaults: protect
  `main`, plus `dev` when `origin/dev` exists), so a field appears only where
  this repo's answer differs from the default, and `"integration_branch": null`
  is how a repo with no integration branch says so out loud.
- **A broken config is not an absent one, and the two layers differ there.** If
  that file is malformed, or is a symlink or directory rather than a regular
  file, `pre-push` fails CLOSED — it refuses every push until the file is fixed
  — while the agent-side hook falls back to no-op. So a repo in that state is
  half-guarded and unpushable: repair the file (or delete it, which opts the
  repo out deliberately), and read `pre-push`'s message rather than guessing —
  it names the field and the value it refused.
- **Two layers read that one file, and they are not alternatives.**
  - `pre-push` is the one that HOLDS: git hands it the resolved refs, so it
    covers humans, scripts and agents alike and refuses a push landing on a
    guarded branch. It yields to **`git push --no-verify`** and to nothing else
    — that is the deliberate override, not the normal route.
  - the `git-workflow` PreToolUse hook is the speed bump in front of it: it sees
    Claude tool calls only, but it catches `git commit` (which never reaches
    `pre-push`) and explains the route before the command runs. Turn it off with
    **`/guard git-workflow off`** when a deliberate override is wanted; that
    disarms only this layer, never `pre-push`.
- Neither layer is a hand-copied file. Both ship with the qute-essentials
  plugin — a `.claude/hooks/git-workflow-guard.py` checked into this repo is a
  stale fork of the plugin's guard and belongs deleted, not maintained.
