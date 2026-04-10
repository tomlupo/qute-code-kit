---
description: One-time setup for /ship in the current project
allowed-tools: Bash(python:*)
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
