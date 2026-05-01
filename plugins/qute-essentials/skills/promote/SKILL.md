---
name: promote
description: Run the subsystem-promotion workflow. Resolves the subsystem alias against the project's CLAUDE.md::Subsystems registry, reads gates from the latest spec frontmatter under `research/{subsystem}/docs/`, runs each gate, then merges to `dev` (default) and applies an annotated `{alias}-vX.Y.Z` tag on the merge commit. No `.claude/promote.config.yaml` — the spec frontmatter is the source of truth. Pairs with `/ship` for the dev → main release-train ceremony. Use when the user says "promote {alias}", "cut {alias}-vX.Y.Z", or asks to ship a new model version.
argument-hint: "<alias-or-subsystem-name> [--version vX.Y.Z] [--target=<branch>] [--no-gates] [--no-tag] [--dry-run]"
---

# /promote

Run the subsystem-promotion ceremony for one model. Reads gates from the spec frontmatter, runs them, merges the current branch to `dev` (or `--target=<branch>`), and applies an annotated `{alias}-vX.Y.Z` tag on the merge commit.

Pairs with `/ship`: `/promote {alias}` ships per-subsystem model versions to `dev`; `/ship` later cuts the repo-wide release train (`vX.Y.Z`) from `dev` to `main`.

## When to use

Invoke when:
- User says "promote {alias}" / "cut {alias}-vX.Y.Z" / "ship the new {alias} version"
- A spec under `research/{subsystem}/docs/` is `status: LOCKED` and ready to deploy
- A `feat/{alias}-{slug}` or `research/{alias}-{slug}` branch is ready for dev integration

Do NOT invoke for:
- Documentation-only PRs (use `/ship` for the release train, no per-subsystem tag)
- Aliases not present in the project's `/CLAUDE.md::Subsystems` table

## Arguments

- `<alias-or-subsystem-name>` (required) — short alias (`taa`) or full subsystem name (`tactical-signals`). Resolved against the project's `/CLAUDE.md::Subsystems` table; either form works.
- `--version vX.Y.Z` (optional) — explicit semver. If omitted, ask the user (patch / minor / major) and compute from the previous `{alias}-v*` tag.
- `--target=<branch>` (optional) — merge target. Default `dev`.
- `--no-gates` (optional) — skip gate enforcement entirely. Used during interim periods where a spec doesn't yet declare a `gates:` block. The skill warns clearly when this is in effect.
- `--no-tag` (optional) — merge without applying a tag. Useful for trivial doc-only updates that still belong on a feat branch.
- `--dry-run` (optional) — run gates and report what would happen; do not merge or tag.

## Behavior

### 1. Resolve the subsystem

- Read the project's `/CLAUDE.md`. Look for a section heading "Subsystems" with a markdown table.
- Match the user's argument against the **Alias** column AND the **Subsystem name** column. Either match wins.
- Recover the dir basename (= subsystem name) and the alias from the matched row.
- If `/CLAUDE.md` has no Subsystems table OR the argument matches nothing:
  - Fall back: if `research/{argument}/` exists, treat the argument as both alias and subsystem name.
  - Else: stop with `Unknown subsystem '{arg}'. Add a row to /CLAUDE.md::Subsystems or create research/{arg}/.`

### 2. Locate and load the spec

- Glob `research/{subsystem}/docs/*.md`.
- Parse YAML frontmatter on each. Keep only those with `status: LOCKED`.
- Pick the highest `version` (semver). That's the active spec.
- If none found:
  - With `--no-gates`: continue.
  - Otherwise: stop with `No LOCKED spec at research/{subsystem}/docs/. Add one or pass --no-gates for an interim merge.`

### 3. Resolve the version

- Last subsystem tag: `git tag --list '{alias}-v*' | sort -V | tail -1`. If none, treat as `v0.0.0`.
- Also check legacy: `git tag --list 'prod-{alias}-*' | sort -V | tail -1` and inform the user if the legacy namespace exists.
- If `--version` provided: validate semver shape and check for collision with existing tags.
- Else: ask user `patch / minor / major?` and compute the bump.
- Final tag name: `{alias}-vX.Y.Z` (no date suffix, no `prod-` prefix).

### 4. Branch check

- Current branch must match `feat/{alias}-*` OR `research/{alias}-*`.
- If on any other branch: stop with `Current branch '{cur}' is not feat/{alias}-* or research/{alias}-*. Switch to one before promoting.`
- If on `main` / `dev`: hard-stop.

### 5. Scan related branches (preflight)

Before running gates, surface any other local branches matching the same subsystem that have unique commits not on the merge target. Prevents the case where a subsystem ship goes out while related work sits orphaned on a parked branch — the failure mode is a LOCKED methodology landing on a feat branch and getting left behind when a sibling release ships.

Build the prefix set: start with `{alias}` and `{subsystem-name}` from the resolved Subsystems row; then scan the row's prose (the table cell text) for backticked tokens after phrases like `Historical alias was`, `formerly`, `was`, `aka` — those are alternate prefixes the skill should also include. Example: a row that says ``"Historical alias was `fundsel`"`` adds `fundsel` to the prefix set.

For each ref of shape `feat/{prefix}-*` or `research/{prefix}-*` for any prefix in the set (excluding the current branch):

- `git rev-list --count {target-branch}..{branch}` — count unique commits not on target.
- `git log -1 --format=%cI {branch}` — last commit date.
- If unique-count > 0: list as `{branch} — {n} commits ahead, last {date} ({Nd}d ago)`.

If any are found, surface in the report:

```
⚠️  Related branches with unmerged work share the '{alias}' alias:
  - feat/{alias}-{slug-a} — 3 commits ahead, last YYYY-MM-DD (Nd)
  - research/{alias}-{slug-b} — 8 commits ahead, last YYYY-MM-DD (Md)

These will NOT be in {alias}-v{X.Y.Z}. Continue, or abort to consolidate first?
```

This is a **soft warning** — does not block. The user decides whether to abort and consolidate, or proceed and accept the orphan. Skip silently if none found.

### 6. Run gates

Read the spec frontmatter `gates:` block (skipped when `--no-gates`). For each true-valued key, run the corresponding check:

| Gate key | Check |
|---|---|
| `spec_locked` | Spec frontmatter has `status: LOCKED` |
| `spec_frontmatter_valid` | Spec has `methodology`, `version`, `date_locked`, `status`, `src_paths` |
| `spec_version_matches_tag` | `version` field == the version being promoted |
| `spec_date_current` | `date_locked` within `spec_date_max_age_days` (default 90) of today |
| `src_paths_match` | Spec `src_paths` exist on disk |
| `backtest_required` | At least one commit message OR EXPERIMENTS.md entry references metrics / MLflow run |
| `experiments_entry` | `research/{subsystem}/EXPERIMENTS.md` has an entry dated within 30 days mentioning this version |
| `findings_for_promotion` | At least one `research/{subsystem}/findings/*.md` is reachable from the current branch |
| `status_updated` | `research/{subsystem}/README.md` mtime is newer than the most recent commit on this branch touching `src_paths` |
| `breaking_changes_flagged` | If commit messages mention BREAKING / polarity / schema, the bump must be major (or user must confirm) |

Unknown gate keys → fail with `Unknown gate '{key}' in spec frontmatter. Either implement it in /promote or remove from spec.`

### 7. Report and ask

```
## /promote {alias} — {alias}-v{X.Y.Z}

Subsystem:    {subsystem-name}  (alias: {alias})
Spec:         research/{subsystem}/docs/{spec-file}  (LOCKED {date}, v{X})
Current tag:  {previous}        →  proposed: {alias}-vX.Y.Z
Target:       {target-branch}   (current: {current-branch})

### Gates
✅ spec_locked
✅ spec_frontmatter_valid
✅ backtest_required          metrics in commit a1b2c3d
⚠️  status_updated             README.md mtime older than latest src/ commit (run /handoff?)
❌ experiments_entry           no entry in EXPERIMENTS.md mentioning v{X.Y.Z}

Stop. Fix the failing gates and re-run, or pass --no-gates to override.
```

If any gate fails (and not `--no-gates`): stop and report.
If any gate produces a soft warning: prompt the user to continue or fix.

### 8. Merge and tag (unless `--dry-run`)

After the user confirms (or `--dry-run` skips this):

1. Open / fast-forward a PR `current-branch → {target-branch}` (default `dev`).
   - PR title: `promote({alias}): v{X.Y.Z} — <short-description>`
   - PR body: spec link, gate results, breaking-changes section if applicable.
2. Merge the PR (`--squash` or `--merge` per project convention; default `--merge` so the dev-merge commit has the right shape for the tag).
3. On the merge commit:
   - Apply annotated tag: `git tag -a '{alias}-v{X.Y.Z}' <merge-sha> -m "<spec section title> — see PR #N"`
   - Push the tag: `git push origin '{alias}-v{X.Y.Z}'`
4. With `--no-tag`: skip step 3 entirely.

### 9. Post-promotion housekeeping (the skill performs this)

- Append to `research/{subsystem}/EXPERIMENTS.md`:
  ```markdown
  ## YYYY-MM-DD — Promoted {alias}-v{X.Y.Z}
  - Tag: {alias}-v{X.Y.Z}
  - Spec: research/{subsystem}/docs/{file} (v{X.Y})
  - PR: <url>
  - Merge SHA: <sha>
  ```
  (Newest at top per the convention in `.claude/rules/research-workflow.md`.)
- Remind the user: `/ship` is what cuts `vX.Y.Z` on `main` later.

## Output format

```markdown
## /promote {alias} — gate report

**Spec**: research/{subsystem}/docs/{file} (v{X.Y}, LOCKED {date})
**Previous tag**: {alias}-v{prev}    **Proposed**: {alias}-v{new}
**Branch**: {current} → {target}

### Related branches
<list of feat/research branches sharing the alias with unique commits, or "none — no orphan work for this alias">

### Gate results
✅/⚠️/❌ <gate>: <detail>
...

### Next action
<"PR opened at <url>; tag pending merge" OR "Fix gates above" OR "--dry-run; nothing changed">
```

## Conventions

- **Read-only until user confirms.** Show the gate report first; merge + tag only on explicit OK.
- **`--dry-run` is encouraged**, especially the first time a subsystem is promoted under the new ceremony.
- **No `prod-` prefix and no date suffix in new tags.** Legacy `prod-{alias}-vX.Y.Z-YYYYMMDD` tags are retained as history; the skill warns when it sees them but does not migrate.
- **Never force-push. Never skip hooks.**
- **No config file.** The spec frontmatter `gates:` block is authoritative. Adding a new gate is a spec edit, not a config edit.
- **`--no-gates` is loud.** The skill prints a clear banner and asks the user to confirm.

## Coherence with other skills

- `/ship` — repo-wide release train (`vX.Y.Z` on `main`); runs the universal forbidden-paths check at the `dev → main` boundary
- `/status` — read-only "what's in prod right now" per subsystem
- `/handoff` — actively updates `TASKS.md` and root `STATUS.md` Notes; pairs naturally with `/promote` (run `/handoff` first if `status_updated` gate fails)
- `/pickup` — session-start dashboard read of root `STATUS.md` + per-subsystem latest tags

## Example

```
/promote taa --version v5.2.0 --dry-run
```

Resolves `taa` against `/CLAUDE.md::Subsystems`, finds `research/tactical-signals/docs/<latest LOCKED spec>`, runs the gates declared in its frontmatter, reports the outcome without merging or tagging. Drop `--dry-run` once the gates are green.

```
/promote selection --no-gates
```

Interim merge for the `selection` subsystem while the methodology v2 spec is still in flight; warns about no-gates mode and asks the user for the version bump explicitly.

## See also

- `.claude/rules/research-workflow.md` — spec frontmatter schema and lifecycle
- `.claude/rules/git-workflow.md` — two-ceremony tagging (`/promote {alias}-vX.Y.Z` on dev, `/ship vX.Y.Z` on main)
- The project's `/CLAUDE.md::Subsystems` — the alias / subsystem-name registry the skill resolves against
