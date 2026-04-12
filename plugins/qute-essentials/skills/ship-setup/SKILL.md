---
name: ship-setup
description: One-time setup for the ship skill in a Python project. Idempotent — safe to re-run. Adds commitizen as a dev dependency, merges [tool.commitizen] into pyproject.toml, creates CHANGELOG.md from the Keep-a-Changelog template, and creates .github/workflows/release.yml. Use when the user asks to set up release automation, prepare for shipping, configure commitizen, or when the ship skill errors with "run /ship-setup first".
argument-hint: ""
---

# /ship-setup

One-time setup for `/ship` in the current project. Python-only in v1.

The setup script is idempotent — safe to re-run. It will:

1. Add `commitizen` as a dev dependency (via `uv add --dev`)
2. Merge `[tool.commitizen]` into `pyproject.toml`
3. Create `CHANGELOG.md` from the Keep-a-Changelog template (if missing)
4. Create `.github/workflows/release.yml` (if missing)

Each step is skipped if the artifact is already in place.

## Task

Run exactly one command, then report what the script did:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/ship_setup.py
```

Report which steps ran and which were skipped. Then tell the user:

> Review and commit the new/modified files. After the first commit, `/ship` is ready to use on the `main` branch.

**Do not** stage or commit anything automatically — let the user review the diff first.

## What the script produces

After running, the project will have:

```
pyproject.toml        ← [tool.commitizen] block added (or merged)
CHANGELOG.md          ← Keep-a-Changelog template (if new)
.github/workflows/
  release.yml         ← Auto-release on push to main (if new)
```

The `[tool.commitizen]` block in `pyproject.toml` looks like:
```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
version_scheme = "semver"
version_provider = "pep621"
update_changelog_on_bump = true
```

## Gotchas

- **`[tool.commitizen]` will be overwritten** on re-run — review the diff before committing if you have customized it
- **`uv` must be on PATH** — the script adds commitizen via `uv add --dev`; if uv is not installed, the script will error
- **CHANGELOG.md is only created if missing** — if it already exists (even empty), it is not touched
- **After setup, write at least one Conventional Commit before running `/ship`** — `/ship` needs commit history to parse; running it immediately after setup with no commits produces "nothing to release"
- **`.github/workflows/release.yml` is CI-optional** — if you don't use GitHub Actions, you can delete it and run `/ship` manually from the CLI

## Related

- `/ship` — the release skill that this sets up for
- `generating-commit-messages` skill — write commits that `/ship` can parse
