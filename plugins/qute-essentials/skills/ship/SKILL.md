---
name: ship
description: Cut a release for the current project. One entry point, two modes — Plugin (marketplace.json present → delegates to scripts/release-plugin.sh) and Python (pyproject.toml → bumps via commitizen). Updates `CHANGELOG.md` and creates an annotated `vX.Y.Z` git tag from Conventional Commits since the last release. The BRANCH selects bump-vs-tag — integration branch bumps only, `/ship --tag` on the release branch completes a two-stage release, single-branch repos do both at once, any other branch is refused. Refuses to bump if forbidden skill-artifact paths are tracked, if tracked files have uncommitted changes, or if a previous bump is still untagged. First-time setup (commitizen + CHANGELOG + workflow) runs automatically and idempotently for Python projects. Use when the user says "ship it", "cut a release", "bump version", "tag release", or asks to release. Webapps use `gstack ship` instead.
argument-hint: "[plugin-name] [patch|minor|major|X.Y.Z] [--tag] [--dry-run]"
---

# /ship

Cut a release for the current project. Updates `CHANGELOG.md` and creates an
annotated `vX.Y.Z` git tag based on Conventional Commits since the last
release.

`vX.Y.Z` on the **release branch** is the only release-tag namespace. That
branch is `main` by house rule, or whatever `conductor.yml` declares as
`release.branch`.

In Python mode the tag *name* is asked of commitizen itself
(`cz version --project --tag`) rather than re-rendered here, so a custom
`[tool.commitizen] tag_format` — including variables like `$prerelease` /
`$devrelease` that a partial renderer would leave as literals — produces
exactly the tag cz used when it computed the version and changelog. If cz
cannot be asked, /ship falls back to local rendering and says so in its
output.

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

## The branch selects the act (ADR-0008)

Bump and tag are **separate acts**, and the branch you are standing on picks
which one happens. No flag is required and none can be forgotten:

| Where you are | What happens |
|---|---|
| integration branch (`dev`) | bump + changelog + lockfile + commit. **No tag.** |
| release branch, two-stage repo | bare `/ship` refuses; `/ship --tag` completes the release |
| release branch, single-stage repo | bump **and** tag, exactly as before |
| any other branch | **refused**, writing nothing |

**Which branch is which.** Release branch = `main`, integration branch = `dev`,
by house rule. A repo's `conductor.yml` may declare `release.branch`, and that
declaration wins — the release tool and the dispatch policy must not disagree.
Two-stage is derived from whether `origin/dev` exists (a local ref read, no
network). `origin/HEAD` is deliberately not consulted: it is unset in a good
share of real clones.

A repo with **no `main`** falls back to `master` if it has one — a pre-`main`
repo still needs to be able to release. If it has neither and declares nothing,
`/ship` says exactly that and asks for a `release.branch` declaration rather
than guessing. Either branch counts whether it is local or only `origin/<name>`
(a `git clone -b dev` has no local `main`).

**Why the branch and not a flag.** The failure this replaces was a correctly
documented convention that someone did not apply in the moment. A flag
reproduces that failure exactly. You cannot not be on a branch.

**Why a feature branch is refused.** Bumping there computes a changelog from a
branch usually behind integration — release metadata describing code that is
not the release — and leaves the new version untagged, which then blocks the
next real release.

### `/ship --tag` — completing a two-stage release

Run on the release branch **after** the release PR has merged. It asserts four
things before creating anything:

1. the remote is reachable (it fetches `--tags`; offline is a refusal, because
   this step both verifies against and publishes to the remote);
2. the local branch matches its remote — the tag must name the commit everyone
   else can see;
3. the version declared at the **tip** (read out of the commit, not the working
   tree) is the version being tagged, and matches any `X.Y.Z` you named;
4. the tag does not already exist.

Then it creates the annotated tag **and pushes it**. Pushing is deliberate: not
pushing fails silently and late — the tag sits local, everything looks green,
and it surfaces when a consumer cannot resolve the ref. Pushing wrongly fails
loudly and immediately, because `release-tag-guard.yml` asserts on push that the
tagged commit is an ancestor of the release branch.

Cutting the tag here, after the merge, is what makes **squash-merging a release
PR safe**: a tag cut on `dev` before the merge points at a commit the squash
never makes an ancestor of `main` (quantbox `v0.4.0`, re-cut as `v0.4.1`).

`/ship --tag --dry-run` runs every assertion and creates nothing.

### Bump in flight

Between the bump and the tag, the declared version has no tag — and commitizen
computes the next increment from the **last tag**. A second `/ship` in that
window would compute off a stale baseline and double-bump, so it is refused.

Two exceptions: a repo with no release tags at all is a first release, and the
tag fetch is best-effort so being offline never blocks a release.

Accepted consequence: **an abandoned bump is sticky.** The refusal names both
exits — finish the release (`/ship --tag` on the release branch) or revert the
bump commit. A stuck release is loud; a double-bump is silent.

### Explicit overrides

`--bump-only`, `--bump-and-tag` and `--tag` pick the act directly. Use
`--bump-and-tag` for a hotfix cut straight on the release branch of a two-stage
repo. They pick the **act**, never the branch: a feature branch is still
refused with any of them.

### Plugin mode

`release-plugin.sh` bumps and tags in one step and `/ship` does not own its
tagging path, so plugin mode has no bump/tag split. It applies the half of the
rule that does transfer: plugin releases must be cut on the release branch, and
any other branch is refused before the release script runs.

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
- Python mode: `[patch|minor|major|X.Y.Z]` and/or `--dry-run`, `--increment`,
  `--tag`, `--bump-only`, `--bump-and-tag`

Report:
- the new version
- the tag that was created (annotated `vX.Y.Z`) — **or, on the integration
  branch, that no tag was created and that `/ship --tag` on the release branch
  is the next step.** Do not paper over this: a bump commit where someone
  expected a release is surprising, and an unexplained surprise gets "fixed" by
  a hand-cut tag, which is the failure the split removes.
- a one-line summary of the CHANGELOG entries that were added

**Do not** stage, commit, push, or modify anything beyond what `ship.py`
does itself, and **never create a release tag by hand** — `/ship` owns the only
tagging path. After a bump the caller pushes the branch (`git push`, or
`git push --follow-tags` in a single-stage repo, where the tag was created
locally). `/ship --tag` pushes its own tag.

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

### Forbidden paths (both modes)

Refuses to release if any tracked file lives under one of these universal
paths (skill-generated artifacts that should not reach main). The gate runs
before mode dispatch, so plugin mode is covered too:

- `docs/superpowers/`
- `docs/specs/`
- `.claude/handoffs/`
- `.claude/skill-use-log.jsonl`

Projects may add extras in `.claude/forbidden-paths.txt` (one path per
line; blank lines and `# comments` allowed).

### Clean working tree (Python mode)

Refuses to bump if **any tracked file** has uncommitted changes — the same
gate `release-plugin.sh` has always applied in plugin mode. The bump commit
stages whole files, so an unrelated local edit would land inside the release
commit and inside the annotated tag that points at it. The error names every
dirty path; commit or stash them and re-run.

**Untracked files never block.** A lockfile, scratch output or a stray build
artifact is routine and is ignored (`git status --untracked-files=no`). Only
*modifications to tracked files* are refused.

The check runs **before** first-time setup, because setup legitimately writes
to `pyproject.toml` / `CHANGELOG.md`; those writes still land in the bump
commit as before. With `--dry-run` the dirty paths are **reported, not
refused** — a dry run creates no commit and no tag, so nothing can be
contaminated.

### TASKS.md::Completed wipe (Python mode, auto)

After cz bump succeeds, the script removes any `## Completed (…)` sections
from `TASKS.md` (work just shipped, canonical record is now `CHANGELOG.md`)
and creates a follow-up commit `chore(tasks): wipe Completed after vX.Y.Z`.
The bump commit + tag stay untouched. This is a **Tier-1 convenience only**:
skipped silently if `TASKS.md` is missing or is a migration tombstone (a repo
that graduated to GitHub Issues tracks completion in the Issues tab, not here).

### First-time setup (Python mode, auto + idempotent)

Each artifact is checked independently — missing ones are created, present
ones are left alone:

1. `commitizen` as a dev dependency (skipped if already in `pyproject.toml`).
2. `[tool.commitizen]` block in `pyproject.toml`. Before seeding, setup
   **reconciles the version** across `{[project] version, latest vX.Y.Z tag,
   stray __version__ literals}`: it seeds cz from the highest and aligns the
   others, so a repo whose tags ran ahead of `pyproject.toml` (e.g. tags cut
   by hand) doesn't seed at a stale version and collide on the first bump.
   Stray `__version__` literals (e.g. `src/pkg/__init__.py`) are added to
   `version_files` so they bump in lockstep; a `__version__` derived from
   `importlib.metadata` is left alone.
3. `CHANGELOG.md` from the Keep-a-Changelog template.
4. ~~`.github/workflows/release.yml`~~ — **no longer created.** It ran `cz bump`
   on every push to main, i.e. /ship's own job, so repos ended up with two
   version writers. Setup now only WARNS if such a workflow already exists.

Re-running `/ship` after the first call is safe — already-present artifacts
are skipped with a one-line note.

### `--dry-run` (Python mode)

**A dry run writes nothing** — no files, no dependency install, no commit, no
tag. It is safe on a repo you have not committed yet: `git status` after a dry
run looks exactly as it did before.

That includes first-time setup, which used to run for real even under
`--dry-run`. It now *reports* each step it would take instead of taking it:

```
ship-setup: would add commitizen as a dev dependency (`uv add --dev commitizen`)
ship-setup: would align pyproject [project] version 0.1.0 -> 0.5.0
ship-setup: would add [tool.commitizen] block (version 0.5.0, 2 version file(s) tracked)
ship-setup: would align src/demo/__init__.py __version__ 0.2.0 -> 0.5.0
ship-setup: would create CHANGELOG.md from template
```

Everything read-only still runs, so the report is real: the forbidden-paths
check, the git tag query, and the version reconciliation that picks the seed
from `{[project] version, latest vX.Y.Z tag, stray __version__ literals}`.

On a repo that is **already configured**, the dry run goes on to `cz bump
--dry-run` and previews the next version and CHANGELOG entries. On a repo that
is **not yet configured** it stops after the setup report — there is no
`[tool.commitizen]` block for cz to bump against, and reaching for cz through
`uv run` would materialize `.venv`/`uv.lock` in the tree the dry run promised
to leave alone. Apply setup for real (`/ship` without `--dry-run`) to preview
the bump itself.

### Plugin-mode invariants (enforced by `release-plugin.sh`)

- Refuses to bump if `.claude-plugin/plugin.json::version` and
  `marketplace.json` catalog version disagree before the bump (drift detector).
  The pre-commit hook in `.githooks/pre-commit` blocks future drift.
- After bump, regenerates `marketplace.json` from plugin manifests (one-way
  flow: hand-edit `.claude-plugin/plugin.json`; `marketplace.json` is derived).

## Who owns the version

Exactly one thing may write versions and tags. Two writers double-bump, and in a
`dev -> main` flow the CI bump lands on `main` as a commit `dev` never sees — the
branches diverge and every later bump computes from a stale baseline.

| Flow | Owner | Notes |
|---|---|---|
| `dev -> main` via release PR (default) | **`/ship` on `dev`**, then **`/ship --tag` on `main`** | The bump reaches `main` through the PR, so both branches match; the tag is cut afterwards, on `main`. |
| Single branch | **`/ship` on the release branch** | Bump and tag in one act. |
| Single branch, CI-owned | the workflow | Copy `templates/github-workflow-release.yml` deliberately and stop using /ship's bump. |

After a release, `main` and the integration branch must agree:
`git diff origin/main origin/dev -- pyproject.toml` — empty is correct.

`templates/release-tag-guard.yml` is the detector for the same failure from the
other side: it fires on every pushed `v*` tag and asserts the tagged commit is
an ancestor of the release branch. It catches hand-cut tags `/ship` never sees,
so the two are complements, not alternatives.

Note: an existing `release.yml` cannot simply be deleted if setup ever created
it — check nothing recreates it. Making the trigger `workflow_dispatch` only is
the stable way to neuter it.

## Gotchas

- **Forbidden path tracked** → strip the files (e.g. `git rm -r docs/superpowers
  && git commit -m 'chore: strip skill artifacts before release'`) and re-run.
- **No Conventional Commits since last tag** → cz exits with "nothing to
  release"; you need at least one `feat:`, `fix:`, or `perf:` commit since
  the last tag.
- **`BREAKING CHANGE:` must be in the commit footer** (not the subject)
  to trigger a major bump — alternatively, append `!` after the type:
  `feat!: remove old API`.
- **Last tag doesn't match `pyproject.toml` version** → *first-time setup*
  now auto-reconciles this (seeds from the highest, aligns the rest). If
  drift is reintroduced *after* setup — e.g. someone cuts a `git tag` by hand
  instead of via `/ship` — `cz bump` can compute unexpected versions. Don't
  hand-tag; verify with `git tag --list 'v*' | sort -V | tail -5` if a bump
  looks off.
- **Uncommitted changes to tracked files** → the bump is **refused**, with
  every dirty path named. Commit or stash them first; a release is cut from a
  clean tree. `--dry-run` reports them instead of refusing. (`--tag` does not
  run this gate: a tag names a commit, so a dirty file cannot ride into it, and
  the version it *could* corrupt is covered by the tip-version assertion.)
- **Untracked files** → harmless, never block. Lockfiles, scratch output and
  build artifacts are routinely untracked, so they are ignored outright.
- **"a bump is already in flight"** → the declared version has no tag. Finish
  the release with `/ship --tag` on the release branch, or revert the bump
  commit. The message names both, and the commit it means.
- **Wrong branch** → `/ship` refuses and writes nothing. Check out the
  integration branch to bump, or the release branch to tag.
- **Lockfile** → a tracked `uv.lock` is refreshed into the bump commit
  (`uv lock`). Best-effort: if the refresh fails, `/ship` warns and continues
  rather than blocking an otherwise correct release.

## Related

- `generating-commit-messages` skill — Conventional Commits so `/ship` can parse version bumps
