---
name: ship
description: Cut a release for the current project. Two modes — Python (bumps `pyproject.toml::version` via commitizen) and Plugin (bumps `plugins/<name>/plugin.json` and regenerates `.claude-plugin/marketplace.json` via `scripts/release-plugin.sh`). Updates `CHANGELOG.md` and creates an annotated `vX.Y.Z` git tag from Conventional Commits since the last release. Refuses to bump if forbidden skill-artifact paths are tracked. First-time setup (commitizen + CHANGELOG + workflow) runs automatically for Python projects. Use when the user says "ship it", "cut a release", "bump version", "tag release", or asks to release. Webapps use `gstack ship` instead.
argument-hint: "[plugin-name] [patch|minor|major|X.Y.Z]"
---

# /ship

Cut a release for the current project. Updates `CHANGELOG.md` and creates an
annotated `vX.Y.Z` git tag based on Conventional Commits since the last
release.

`vX.Y.Z` on `main` is the only release-tag namespace. Per-subsystem semver
(formerly via `/promote`) is retired; track subsystem-level changes with
`git log --first-parent -- src/{subsystem}/`.

## Mode dispatch

Detect mode by what's in the repo root:

1. **`.claude-plugin/marketplace.json` exists** → **Plugin mode**. The repo
   is a plugin marketplace (one or more `plugins/<name>/plugin.json` files).
   Run `scripts/release-plugin.sh <plugin-name> <bump-or-version>`. Args:
   - `<plugin-name>` — required if the marketplace contains more than one
     plugin. If only one, default to that one and confirm with the user.
   - `<bump-or-version>` — `patch`, `minor`, `major`, or an explicit
     `X.Y.Z`. Choose `minor` for new features, `patch` for fixes only,
     `major` for breaking changes (or any commit with a `!` type or
     `BREAKING CHANGE:` footer since the last tag).
2. **`pyproject.toml` exists** (and no marketplace.json) → **Python mode**.
   Run the commitizen-driven script (below).
3. **Otherwise** → fail with a message naming what was missing.

The first-time-setup behavior (commitizen, CHANGELOG template,
release.yml) only applies to Python mode. Plugin mode assumes the
marketplace repo already has its `scripts/build-marketplace.py` build
machinery in place and a `CHANGELOG.md` at the repo root.

Webapps: use `gstack ship` from the shell instead.

## Pre-bump gates

Before invoking either mode's bump, run two checks. Treat them as
release gates — releasing over a red gate is the kind of thing the
release commit should explicitly note as a skip.

1. **Tests** — run `/test`. Refuse to proceed on failures unless the
   user explicitly says to ship anyway ("ship anyway", "skip tests",
   "skip gates"). Skip silently if no test framework is detected —
   that is not a failure, just an absence.
2. **Dep audit** (Python mode only) — run `/audit`. Surface findings.
   Warn loudly if CVEs are found, but do **not** block — audit
   results are informational, not gating. Skip in plugin mode.

When the user explicitly bypasses gates, mention the skip in the
release commit body so the audit trail captures *why* the release went
out without verification.

## Task — Plugin mode

```bash
scripts/release-plugin.sh <plugin-name> <patch|minor|major|X.Y.Z>
```

Report:
- the new version (printed by the script as `✓ Released <plugin> vX.Y.Z`)
- the tag that was created
- a one-line summary of the CHANGELOG entries that were added

The script refuses to bump if `plugin.json` and `marketplace.json` versions
disagree before the bump. If you hit that error, the drift must be fixed
manually (pick the higher version, edit `plugin.json` to match, rerun) —
this only happens once per repo when migrating into the lockstep model.

The pre-commit hook in `.githooks/pre-commit` blocks future drift
automatically.

**Do not** stage, commit, push, or modify anything beyond what the script
does itself. The script already produces the `chore(release): bump …`
commit and the `vX.Y.Z` tag. Caller pushes:  `git push --follow-tags`.

## Task — Python mode

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

### TASKS.md::Completed wipe (auto)

After cz bump succeeds, the script removes any `## Completed (…)` sections from `TASKS.md` (work just shipped, the canonical record is now `CHANGELOG.md`) and creates a follow-up commit `chore(tasks): wipe Completed after vX.Y.Z`. The bump commit + tag stay untouched. Skipped silently if `TASKS.md` is missing.

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
  these artifacts on `main` create durable noise that `/handoff` relies
  on never reaching prod.
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

- `generating-commit-messages` skill — Conventional Commits so `/ship` can parse version bumps
