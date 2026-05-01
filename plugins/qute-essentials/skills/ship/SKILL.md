---
name: ship
description: Cut a release for the current Python project. Bumps `pyproject.toml::version`, updates `CHANGELOG.md`, and creates an annotated `vX.Y.Z` git tag from Conventional Commits since the last release. Refuses to bump if forbidden skill-artifact paths are tracked. First-time setup (commitizen + CHANGELOG + workflow) runs automatically. Use when the user says "ship it", "cut a release", "bump version", "tag release", or asks to release. Python-only in v1; webapps use `gstack ship` instead.
argument-hint: ""
---

# /ship

Cut a release for the current project. Bumps `pyproject.toml::version`,
updates `CHANGELOG.md`, and creates an annotated `vX.Y.Z` git tag based on
Conventional Commits since the last release. First-time setup runs
automatically.

Pairs with `/promote {alias}`: `/promote` ships per-subsystem model
versions (`{alias}-vX.Y.Z` on `dev`); `/ship` cuts the repo-wide release
train (`vX.Y.Z` on `main`).

Python-only in v1. Webapps: use `gstack ship` from the shell instead.

## Task

Run exactly one command, then report the outcome:

```bash
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/ship.py
```

Report:
- the new version (read it back from `pyproject.toml` if the script doesn't print it clearly)
- the tag that was created (annotated `vX.Y.Z`)
- a one-line summary of the CHANGELOG entries that were added

**If the script errors with "forbidden paths are tracked"**, stop and tell
the user which paths need to be stripped. Do not strip them yourself —
the user decides whether the artifacts are needed locally or should be
removed entirely.

**Do not** stage, commit, push, or modify anything beyond what the script
does itself. The script already produces a `bump:` commit and tag.

## What the script enforces

### Forbidden paths

The script refuses to bump if any tracked file lives under one of these
universal paths (skill-generated artifacts that should not reach main):

- `docs/superpowers/`
- `docs/specs/`
- `.claude/handoffs/`
- `.claude/skill-use-log.jsonl`

Projects may add extras in `.claude/forbidden-paths.txt` (one path per
line; blank lines and `# comments` allowed).

### First-time setup (auto)

If `pyproject.toml` has no `[tool.commitizen]` block, the script runs the
one-time setup before bumping:

1. Adds `commitizen` as a dev dependency (via `uv add --dev`)
2. Merges `[tool.commitizen]` into `pyproject.toml`
3. Creates `CHANGELOG.md` from the Keep-a-Changelog template (if missing)
4. Creates `.github/workflows/release.yml` (if missing)

Each step is idempotent — re-running `/ship` after the first call only
performs the bump. The setup module lives at
`${CLAUDE_PLUGIN_ROOT}/scripts/ship_setup.py`; the prior `/ship-setup`
skill has been folded into `/ship` and is no longer a separate command.

## Gotchas

- **Forbidden path tracked** → the script refuses to bump. Strip the
  files (e.g. `git rm -r docs/superpowers && git commit -m 'chore: strip
  skill artifacts before release'`) and re-run `/ship`. Do not bypass —
  these artifacts on `main` create durable noise that `/handoff` and
  `/promote` rely on never reaching prod.
- **No Conventional Commits since last tag** → the script exits with
  "nothing to release"; you need at least one `feat:`, `fix:`, or
  `perf:` commit since the last tag.
- **`BREAKING CHANGE:` must be in the commit footer** (not the subject)
  to trigger a major bump — alternatively, append `!` after the type:
  `feat!: remove old API`
- **Last tag doesn't match `pyproject.toml` version** → the script may
  compute unexpected bumps; verify with `git tag --list 'v*' | sort -V
  | tail -5` before running.
- **Untracked or uncommitted files** don't affect the bump but appear in
  git noise — commit or stash first for a clean release.
- **First run on a fresh project** → the script auto-runs setup; review
  the diff (`pyproject.toml`, `CHANGELOG.md`, `.github/workflows/release.yml`)
  and commit those before re-invoking `/ship` for the actual bump.

## Related

- `/promote {alias}` — per-subsystem model promotion (`{alias}-vX.Y.Z` on `dev`)
- `generating-commit-messages` skill — Conventional Commits so `/ship` can parse version bumps
