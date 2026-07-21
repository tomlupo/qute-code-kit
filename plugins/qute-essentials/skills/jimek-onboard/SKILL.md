---
name: jimek-onboard
description: >-
  One command to make a repo Jimek-managed. Detects the target repo's workflow
  conventions (PR base branch, whether direct commits to default are allowed,
  live-capital status, release/tag conventions) and STAMPS a schema-valid
  `conductor.yml` (the per-repo Jimek dispatch + workflow-policy contract) plus the
  `review-gate` CI, idempotently — never clobbering an existing file (backs up +
  diffs instead). The generated contract is validated against the REAL loader
  (dispatcher.jimek.load_contract on origin/master) before it is written. Use
  when onboarding a repo to the Jimek fleet. Triggers: /jimek-onboard, "onboard
  this repo to jimek", "make this repo jimek-managed", "jimek setup".
argument-hint: "[--dry-run | --print | --force | --no-review-gate] [--repo DIR]"
---

# jimek-onboard

Stamp Jimek's per-repo config into the **current repo** in one command. This is
the qute-essentials repo-distribution mechanism that makes a repo part of the
Jimek fleet. It is deliberately separate from orchestration: the contract SCHEMA
lives in `dispatcher.jimek.JimekContract` (the single source of truth — the 8
Wave-1a policy fields plus the core dispatch fields); this skill only *templates*
a schema-valid `conductor.yml` from that schema's shape and the repo's detected
conventions.

## What it does

Run inside a target repo. It is idempotent — safe to re-run:

1. **Detects** the repo's conventions: PR base branch (`dev` for dm-evo/quantbox
   or repos whose docs say "PR to dev"; `main` otherwise), whether direct commits
   to the default branch are allowed (→ trivial tier `commit-to-default` vs `pr`),
   whether it is live-capital (→ records `escalation.block_on`; the dispatcher
   rigor engine already forces live-capital changes to complex + a Tom gate),
   and release/tag conventions (from `pyproject.toml` commitizen `tag_format`).
2. **Stamps `conductor.yml`** at the repo root, templated from the detected
   conventions + the schema. It is **validated** first by a bundled structural
   check (guards the W1c `"commit"` bug — `path` must be `commit-to-default` |
   `pr` only) and then by the **authoritative** loader extracted from
   `origin/master` of a local dispatcher checkout. A rejected contract fails the
   run loudly; a missing dispatcher checkout downgrades to the bundled check with
   a warning.
3. **Stamps `.github/workflows/review-gate.yml`** (require-independent-reviewer)
   if absent.
4. **Prints a summary** of what it detected + stamped, and the next step
   (commit + PR to the detected base via `/qute-coder`).

Existing files are never blind-clobbered: an identical file is a no-op; a
differing file prints a unified diff and writes a `*.jimek-proposed` sibling
(apply with `--force`, which backs the original up to `*.bak` first).

## Run it

```bash
# Detect + validate + stamp into the current repo:
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/jimek_onboard.py $ARGUMENTS

# Preview the generated conductor.yml without writing anything:
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/jimek_onboard.py --print

# Dry-run (detect + render + validate, write nothing, show the diffs):
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/jimek_onboard.py --dry-run
```

Flags: `--repo DIR` (target a repo other than cwd), `--dispatcher-repo DIR` (or
`$DISPATCHER_REPO`; where the authoritative loader is read from — defaults to
`~/workspace/projects/jimek`), `--force` (back up + overwrite existing
files), `--no-review-gate` (skip the CI stamp), `--print`, `--dry-run`.

## After stamping

- Review `conductor.yml` and any `*.jimek-proposed`.
- Commit on a branch and open a PR to the detected base branch (`/qute-coder`).
- The dispatcher hot-reloads contracts (`/jimek/reload`); a broken contract is
  fail-closed (the repo has NO contract until fixed) — so the pre-write
  validation matters.

## Files

- `scripts/jimek_onboard.py` — detect + template + validate + stamp (this skill's engine).
- Contract schema (source of truth): `dispatcher/src/dispatcher/jimek.py`, `dispatcher/docs/jimek-contract.md`.
