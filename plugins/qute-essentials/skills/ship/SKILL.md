---
name: ship
description: Cut a release for the current Python project. Bumps the version in pyproject.toml, updates CHANGELOG.md, and creates a git tag based on Conventional Commits since the last release. Use when the user says "ship it", "cut a release", "bump version", "tag release", or asks to release. Python-only in v1; webapps should use `gstack ship` from the shell instead. Requires one-time setup via the ship-setup skill.
argument-hint: ""
---

# /ship

Cut a release for the current project. Bumps the version in
`pyproject.toml`, updates `CHANGELOG.md`, and creates a git tag based on
Conventional Commits since the last release.

Python-only in v1. Webapps: use `gstack ship` from the shell instead.

## Task

Run exactly one command, then report the outcome:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/ship.py
```

Report:
- the new version (read it back from `pyproject.toml` if the script doesn't print it clearly)
- the tag that was created
- a one-line summary of the CHANGELOG entries that were added

**If the script errors with "run /ship-setup first"**, stop and tell the user to run `/ship-setup`. Do NOT try to set things up yourself.

**Do not** stage, commit, push, or modify anything beyond what the script does itself. The script already produces a `bump:` commit and tag.

## Related

- `/ship-setup` — one-time setup required before first `/ship` in a project
- `generating-commit-messages` skill — ensures commit messages follow Conventional Commits so `/ship` can parse version bumps
