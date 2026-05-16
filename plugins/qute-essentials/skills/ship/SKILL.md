---
name: ship
description: Cut a release for the current project. One entry point, two modes — Plugin (marketplace.json present → delegates to scripts/release-plugin.sh) and Python (pyproject.toml → bumps via commitizen). Updates `CHANGELOG.md` and creates an annotated `vX.Y.Z` git tag from Conventional Commits since the last release. Refuses to bump if forbidden skill-artifact paths are tracked. First-time setup (commitizen + CHANGELOG + workflow) runs automatically and idempotently for Python projects. Use when the user says "ship it", "cut a release", "bump version", "tag release", or asks to release. Webapps use `gstack ship` instead.
argument-hint: "[plugin-name] [patch|minor|major|X.Y.Z] [--dry-run]"
---

# /ship

Cut a release for the current project. Updates `CHANGELOG.md` and creates an
annotated `vX.Y.Z` git tag based on Conventional Commits since the last
release.

`vX.Y.Z` on `main` is the only release-tag namespace.

## Mode dispatch (handled by `ship.py`)

The script auto-detects mode by what's in the repo root:

1. **`.claude-plugin/marketplace.json` exists** → **Plugin mode**.
   `ship.py` delegates to `scripts/release-plugin.sh <plugin> <bump-or-version>`.
   - `<plugin>` — required if the marketplace contains more than one plugin.
     If only one, omit and `ship.py` will pick it.
   - `<bump-or-version>` — `patch`, `minor`, `major`, or explicit `X.Y.Z`.
     Choose `minor` for new features, `patch` for fixes only, `major` for
     breaking changes (or any commit with a `!` type / `BREAKING CHANGE:`
     footer since the last tag).
2. **`pyproject.toml` exists** (and no marketplace.json) → **Python mode**.
   Commitizen-driven; see "Python mode" below.
3. **Otherwise** → fails with a message naming what was missing.

Webapps (`package.json` at the root): use `gstack ship` from the shell instead.

## Pre-bump gates (LLM-driven)

`ship.py` itself does not run tests or audits — those gates are the model's
responsibility, run before invoking `/ship`:

1. **Tests** — run `/test`. Refuse to proceed on failures unless the user
   explicitly says to ship anyway ("ship anyway", "skip tests", "skip
   gates"). Skip silently if no test framework is detected.
2. **Dep audit** (Python mode only) — run `/audit`. Surface findings.
   Warn loudly if CVEs are found, but do **not** block — audit results
   are informational, not gating.

When the user explicitly bypasses gates, mention the skip in the release
commit body so the audit trail captures *why* the release went out
without verification.

## Invocation

In all cases, run exactly one command and report the outcome:

```bash
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/ship.py [args]
```

`ship.py` dispatches to the correct mode. Pass through the user's args:
- Plugin mode: `[<plugin>] <bump|version>`
- Python mode: `[patch|minor|major|X.Y.Z]` and/or `--dry-run`, `--increment`

Report:
- the new version
- the tag that was created (annotated `vX.Y.Z`)
- a one-line summary of the CHANGELOG entries that were added

**Do not** stage, commit, push, or modify anything beyond what `ship.py`
does itself. The downstream script already produces the bump commit and
the `vX.Y.Z` tag. Caller pushes: `git push --follow-tags`.

**If the script errors with "forbidden paths are tracked"**, stop and tell
the user which paths need to be stripped. Do not strip them yourself —
the user decides whether the artifacts are needed locally or should be
removed entirely.

### After the release: end-user upgrade path

Once the tag is pushed, end-users update their installed plugin via the
official CLI:

```bash
claude plugin update <plugin-name>@<marketplace-name>
# e.g. claude plugin update qute-essentials@qute-marketplace
```

A running session then needs `/reload-plugins` (or a full restart) to
apply. Mention this in the report you give the user after a successful
release — closes the loop on "shipped → installed".

## What `ship.py` enforces

### Forbidden paths (Python mode)

Refuses to bump if any tracked file lives under one of these universal
paths (skill-generated artifacts that should not reach main):

- `docs/superpowers/`
- `docs/specs/`
- `.claude/handoffs/`
- `.claude/skill-use-log.jsonl`

Projects may add extras in `.claude/forbidden-paths.txt` (one path per
line; blank lines and `# comments` allowed).

### TASKS.md::Completed wipe (Python mode, auto)

After cz bump succeeds, the script removes any `## Completed (…)` sections
from `TASKS.md` (work just shipped, canonical record is now `CHANGELOG.md`)
and creates a follow-up commit `chore(tasks): wipe Completed after vX.Y.Z`.
The bump commit + tag stay untouched. Skipped silently if `TASKS.md` is
missing.

### First-time setup (Python mode, auto + idempotent)

Each artifact is checked independently — missing ones are created, present
ones are left alone:

1. `commitizen` as a dev dependency (skipped if already in `pyproject.toml`).
2. `[tool.commitizen]` block in `pyproject.toml`.
3. `CHANGELOG.md` from the Keep-a-Changelog template.
4. `.github/workflows/release.yml`.

Re-running `/ship` after the first call is safe — already-present artifacts
are skipped with a one-line note.

### Plugin-mode invariants (enforced by `release-plugin.sh`)

- Refuses to bump if `.claude-plugin/plugin.json::version` and
  `marketplace.json` catalog version disagree before the bump (drift detector).
  The pre-commit hook in `.githooks/pre-commit` blocks future drift.
- After bump, regenerates `marketplace.json` from plugin manifests (one-way
  flow: hand-edit `.claude-plugin/plugin.json`; `marketplace.json` is derived).

## Gotchas

- **Forbidden path tracked** → strip the files (e.g. `git rm -r docs/superpowers
  && git commit -m 'chore: strip skill artifacts before release'`) and re-run.
- **No Conventional Commits since last tag** → cz exits with "nothing to
  release"; you need at least one `feat:`, `fix:`, or `perf:` commit since
  the last tag.
- **`BREAKING CHANGE:` must be in the commit footer** (not the subject)
  to trigger a major bump — alternatively, append `!` after the type:
  `feat!: remove old API`.
- **Last tag doesn't match `pyproject.toml` version** → verify with
  `git tag --list 'v*' | sort -V | tail -5` before running.
- **Untracked or uncommitted files** don't affect the bump but appear in
  git noise — commit or stash first for a clean release.

## Related

- `generating-commit-messages` skill — Conventional Commits so `/ship` can parse version bumps
