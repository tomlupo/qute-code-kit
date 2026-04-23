---
name: promote
description: Run the research-to-production promotion workflow for a specific subsystem. Validates that spec is locked, backtest ran, STATUS.md is updated, and a proper feat/ branch is in use. Reads `.claude/promote.config.yaml` to determine per-subsystem gates. Opens a promotion PR with the filled template. Use when the user says "promote X to production", "ship {subsystem}", "cut prod-{subsystem}-vX.Y.Z", or references the promote.config.yaml gating. Pairs with /ship (general PR-to-main shipping) but adds methodology-specific gating.
argument-hint: "<subsystem-slug> [--version vX.Y.Z] [--dry-run]"
---

# /promote

Manage the research → production lifecycle for a specific subsystem (e.g. tactical signals, fund selection ML). Enforces gating checks from `.claude/promote.config.yaml` before merging research work to `main`.

Complements `/ship` (general PR-to-main shipping). Use `/promote` when releasing a new version of a model / methodology and you want the full checklist enforcement. Use `/ship` for small patches and ad-hoc merges.

## When to use

Invoke when:
- User says "promote {subsystem} to production" / "ship the new {subsystem} version"
- Research methodology is locked and ready to be deployed
- User wants to cut a new `prod-{subsystem}-vX.Y.Z` tag
- User references a specific feat branch that's ready for main promotion

Do NOT invoke for:
- Small bug-fix patches (use `/ship` instead)
- Documentation-only PRs
- Subsystems not declared in `.claude/promote.config.yaml`

## Arguments

- `<subsystem-slug>` (required) — e.g. `taa`, `fundsel`, `extract`. Must match a key under `subsystems:` in `.claude/promote.config.yaml`.
- `--version vX.Y.Z` (optional) — the semver to apply. If omitted, infer from last prod tag + user's intent (patch / minor / major bump asked in conversation).
- `--dry-run` (optional) — run all gates but do not open a PR or create a tag.

## Behavior

1. **Load config**:
   - Read `.claude/promote.config.yaml`. If missing → stop with clear error: "No `.claude/promote.config.yaml` — add it to declare subsystems."
   - Validate `<subsystem-slug>` exists under `subsystems:`. If not → stop: "Unknown subsystem '{slug}'. Known: {list}."

2. **Resolve version**:
   - Last prod tag: `git tag --list 'prod-{slug}-*' | sort -V | tail -1`
   - If `--version` provided: use it, verify no collision
   - Else: ask user whether this is patch/minor/major and compute from last prod tag
   - Compute full tag name: `prod-{slug}-vX.Y.Z-YYYYMMDD` (UTC date of PR open)

3. **Branch check**:
   - Current branch must match `feat/{slug}-*` (from `feat_branch_pattern` in config)
   - If on a non-feat branch → stop: "Current branch '{current}' doesn't match feat/{slug}-*. Create one with `git checkout -b feat/{slug}-{meaningful-slug} origin/dev`."
   - If on a long-lived research branch (`research/*`) → hard-stop: "Cannot promote from a research branch. Cherry-pick to a feat/ branch off dev first."

4. **Run gates** (from `subsystems.{slug}.gates`):
   - `spec_locked` — grep the spec file for `LOCKED YYYY-MM-DD` markers. Must have at least one LOCKED section dated within the last 60 days.
   - `backtest_required` — either a metrics table in `git log` messages of this branch, OR an MLflow run ID referenced in an EXPERIMENTS.md entry OR the PR description.
   - `status_updated` — if `status_file` configured, check that its mtime is more recent than the newest commit on this branch touching `src_paths`. If stale → prompt user to update STATUS.md now.
   - `experiments_entry` — if `experiments_file` configured, check that it contains an entry dated within the last 30 days referencing this promotion.
   - `breaking_changes_flagged` — scan commit messages for keywords (`BREAKING:`, `polarity`, `schema`, `semver-major`). If any appear but --version isn't a major bump → prompt to confirm.

5. **Report gate results**:
   ```
   ## Promotion gates for {subsystem} → {version}
   
   ✅ Spec locked: 2026-04-23 (research/tactical-signals/docs/signal-definitions-v4.md §3.5)
   ✅ EXPERIMENTS entry: 2026-04-23 (research/tactical-signals/EXPERIMENTS.md line 5)
   ✅ Backtest metrics: found in commit abc1234 body
   ✅ STATUS.md updated: 2026-04-23 (newer than last src/taa_signals/ commit)
   ⚠️ Breaking changes: commit def5678 says "signal polarity flip" but version is minor — confirm?
   ```
   - If any gate fails hard: stop and report.
   - If any gate needs confirmation: prompt user.

6. **Fill PR template**:
   - Read `.github/pull_request_template/promotion.md`
   - Fill in: subsystem, new/previous versions, spec refs, backtest metrics, breaking changes section
   - Include a link to the MLflow run or backtest output dir

7. **Open PR** (unless `--dry-run`):
   - Target branch: `dev` (per config `integration_branch`)
   - Title: `promote({slug}): vX.Y.Z — {short-description-from-conversation}`
   - Body: filled PR template
   - Post-merge actions listed at bottom

8. **Record the intent**:
   - Append to the subsystem's `EXPERIMENTS.md`:
     ```markdown
     ## YYYY-MM-DD — Promotion PR opened: {slug} vX.Y.Z
     - PR URL: {url}
     - Tag pending: prod-{slug}-vX.Y.Z-YYYYMMDD
     - Will merge to dev, then dev → main, then apply tag
     ```
   - Do NOT apply the tag yet — tagging happens after merge to main.

9. **Remind the user of post-merge actions**:
   ```
   After this PR merges to dev, and dev → main PR lands:
   1. git tag -a prod-{slug}-vX.Y.Z-YYYYMMDD <main-merge-commit> -m "..."
   2. git push origin prod-{slug}-vX.Y.Z-YYYYMMDD
   3. Update STATUS.md "In Production" section on main via a chore commit
   4. Verify cron runs next scheduled execution
   ```

## Output format

```markdown
## /promote {subsystem} — gate report

**Current prod version**: prod-{subsystem}-vX.Y.Z-YYYYMMDD (from git tags)
**Proposed version**: prod-{subsystem}-vA.B.C-YYYYMMDD
**Current branch**: feat/{subsystem}-{slug}

### Gate results
✅/⚠️/❌ <gate name>: <detail>
...

### Next action
<"PR opened at <url>" OR "Fix gates above, then re-run /promote">
```

## Conventions

- **Read-only until user confirms** — show gate results first; open PR only after explicit OK.
- **`--dry-run` is encouraged** — especially for first-time promoting a subsystem.
- **Never auto-tag** — tags are applied manually after the PR merges to main. Skill only reserves the tag name.
- **Never force-push**. Never skip hooks.
- **If config is missing for a gate** (e.g. `backtest_required: false`), skip that gate silently — config is source of truth.

## Coherence with other skills

- `/handoff` — writes session state, flags any `/src/` edits on research branches
- `/pickup` — reads state, loads STATUS.md per subsystem
- `/decision` — creates ADRs that /promote can reference in the PR body
- `/ship` — general PR-to-main shipping without subsystem gating (use for docs/patches)
- **`/promote`** — research-to-production workflow with full gating

## Example

```
/promote taa --version v4.6.0 --dry-run
```

Loads `.claude/promote.config.yaml`, checks that the current branch is `feat/taa-*`, runs the five gates (spec locked, experiments entry, backtest metrics, STATUS.md freshness, breaking changes), and reports the outcome without opening a PR. Use `--dry-run` off when gates pass.

## See also

- `.claude/rules/research-workflow.md` — lifecycle rules
- `.claude/rules/git-workflow.md` — branch strategy + tag format
- `.claude/promote.config.yaml` — per-subsystem gate config
- `.github/pull_request_template/promotion.md` — PR template used here
