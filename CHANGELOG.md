## v2.5.0 (2026-06-11)

### Refactor

- slim to essentials — scope guards, drop redundant hooks/skills

## v2.4.0 (2026-06-02)

### Feat

- reconcile version across pyproject, tags, and __version__ on setup (#44)

## v2.3.0 (2026-05-24)

### Feat

- add /task and rework /board to merge sources
- add unified task engine (pulse.sh) with GitHub source

### Refactor

- retire /issue, board.sh, issue.sh

## v2.2.2 (2026-05-19)

## v2.2.1 (2026-05-19)

## v2.2.0 (2026-05-18)

### Feat

- modernize pyproject templates per osquant 2025 guide (#41)

## v2.1.0 (2026-05-18)

### Feat

- salvage backtest skill + market-datasets instrument schema (#35)

### Fix

- drop jq dependency in release-plugin.sh + pre-commit (#39)
- make plugin hooks Windows-compatible (#38)
- remove broken setup-project.sh symlink (#37)

### Refactor

- unify /ship dispatch; canonicalize .claude-plugin/plugin.json (#33)

## v2.0.0 (2026-05-14)

### BREAKING

- feat(qute-essentials)!: add /issue /board, lean rewrite of /handoff /pickup /status

## v1.21.0 (2026-05-11)

### Feat

- /status detects orphan stashes + merged-PR worktrees

## v1.20.0 (2026-05-11)

### Feat

- /status warns when main checkout drifts off dev

## v1.19.1 (2026-05-09)

### Feat

- pre-push hook enforces release-shape for plugin version bumps

### Fix

- on_notification.py missing platform import

## v1.19.0 (2026-05-09)

### Feat

- **qute-essentials**: `/status` adds TASKS.md::Now row-size lint. Walks
  each `### Title` block under `## Now` (skipping blank lines) and flags
  entries with 5+ lines as candidates for promotion to
  `docs/tasks/{slug}.md`. Backs the row-size discipline added to
  `work-organization.md::Row-size discipline`: pointer-shape Now rows are
  header + `→ plan:` + `→ handoff:` + `Latest:` (4 lines); inline rows
  are 1-3 lines for small tasks without a plan. ## Next and ## Later are
  exempt — bullet-cluster entries (multiple short bullets under one
  cluster header) are legitimate buffer-queue organization.

## v1.18.0 (2026-05-09)

### BREAKING

- **qute-essentials**: lifecycle skills move to the **drift-on-branches**
  model. Handoffs and TASKS.md edits now live on whichever branch the
  work happened on (formerly: dev-only state with cross-tree commit
  ceremony from worktrees). They reach dev via PR merge. `/status`
  walks `git worktree list` to surface in-flight state from every
  active branch — no longer assumes dev is canonical.
  - `/handoff` step 6 simplified: `git add + commit + push` on the
    current branch, no cross-tree dance, no print-commands ceremony.
    Pre-flight check refuses if there are unstaged edits to handoff
    or TASKS.md paths from outside the skill's own writes.
  - `/status` rewritten to walk the worktree umbrella. Each worktree's
    latest handoff (with `status:` and first `next[0].action`) and
    TASKS.md::Now appear in the dashboard, grouped by branch. Orphan
    detection cross-references against the union of `docs/tasks/*.md`
    slugs across all worktrees, not just dev.
  - `/pickup` simplified to a thin wrapper: run /status, smart-pick
    latest in-progress handoff (or filter by explicit slug), load plan
    + handoff (capped at 2 files / 2000 tokens), brief in 150 words.
  - **Migration impact for projects using DR-010-style "TASKS.md is
    dev-only" pre-commit hooks:** drop the hook (or relax it) to allow
    TASKS.md edits on feat/* and research/* branches. Document the
    drift model in your project's work-organization rule.
  - **Filename collision risk:** two branches handing off on the same
    day with the same task slug produce identical filenames. Rare in
    solo work; resolve add/add conflict manually at PR if it happens.

### Refactor

- **qute-essentials**: `/status` smoke-tested at <200ms wall time on a
  ~2-worktree project (frontmatter parsing via awk, no per-handoff
  git operations).

## v1.17.2 (2026-05-09)

### Feat

- native manifest validation in pre-commit + end-user upgrade docs in /ship

### Fix

- handoff YAML frontmatter + derived manifest missing version

## v1.17.1 (2026-05-09)

### Feat

- refactor/perf in CHANGELOG + pyproject sync + auto-stage derived manifest

## v1.17.0 (2026-05-09)

### Feat

- thin /guard and /config skills + config_toggle.py
- /ship pre-bump gates + plugin description fix

### Fix

- ignore untracked files in dirty-tree check

## v1.16.0 (2026-05-09)

### BREAKING

- **qute-essentials**: removed the `forced_eval` UserPromptSubmit hook
  (the "MANDATORY: TOOL ACTIVATION SEQUENCE" wall injected on every
  prompt). Modern Claude models pick up skills from the system prompt
  without a forced YES/NO evaluation pass — the per-turn token cost no
  longer pays for itself. `forced_eval.py` and `forced_eval.sh` remain
  on disk for opt-in revival; only the hook entry is removed from
  `hooks/hooks.json`.
- **qute-essentials**: `langfuse` guard now defaults to
  `enabled: false`. Tracing is still useful for headless / scheduled /
  agentic-cron runs where you can't observe live, but ~2.7s per
  PostToolUse is too costly for interactive sessions. Re-enable per
  session with `/guard langfuse on` or per process with
  `CLAUDE_GUARD_LANGFUSE=1`.

### Feat

- **qute-essentials**: plugin-aware release tooling for marketplace
  monorepos. New `scripts/release-plugin.sh` bumps
  `plugins/<name>/plugin.json` and regenerates
  `.claude-plugin/marketplace.json` atomically (no more drift between
  source-of-truth and catalog), prepends a CHANGELOG entry from
  Conventional Commits since the last `vX.Y.Z` tag, commits, and tags.
  New `.githooks/pre-commit` blocks any future commit that would
  introduce drift between the two version sources. Activate per-clone
  with `git config core.hooksPath .githooks`.
- **qute-essentials**: `/ship` learns plugin-mode dispatch — when the
  current repo has `.claude-plugin/marketplace.json` it routes to
  `scripts/release-plugin.sh` instead of the pyproject/commitizen path.
  Python projects continue through the existing flow unchanged.
- **qute-essentials/wtf**: `/wtf` adds a hookify-rule tier as the third
  guardrail layer (after feedback memory and CLAUDE.md). When a
  frustration maps to a pattern-catchable failure (specific tool +
  input regex, low false-positive rate, high-cost recurrence), `/wtf`
  now also offers a hookify rule alongside the memory and CLAUDE.md
  recording. Behavior failures that aren't regex-matchable stop at
  memory to avoid rule-thicket noise.

### Refactor

- **qute-essentials**: tighten lifecycle skills under the
  single-namespace model. `/handoff` body synthesis is terser (Summary
  2-4 sentences max + Next steps required; Decisions/Risks now
  optional, "skip when work was straightforward"); diff is `git diff
  --stat HEAD~5` instead of full diff. `/pickup` context cap halved (4
  files / 3000 tokens → 2 files / 2000 tokens) with explicit "reading
  more is the speed trap" guidance. `/status` reports `Latest release:
  vX.Y.Z` + commits ahead on `dev`, replacing per-subsystem
  `{alias}-vX.Y.Z` tag queries with `git log --first-parent` against
  production paths from `CLAUDE.md::Subsystems` column 3 (rows whose
  column 3 starts with `(` are reported as `(research-only)`). `/ship`
  documents Plugin / Python mode dispatch explicitly; the prior
  `/ship-setup` skill is now visibly folded in.

## v1.15.0 (2026-05-09)

### BREAKING

- **qute-essentials**: removed the `/promote` skill. Per-subsystem
  promotion ceremony with spec-frontmatter `gates:`, `LOCKED` enforcement,
  and `{alias}-vX.Y.Z` annotated tags is retired in favor of a single
  release namespace (`vX.Y.Z` set by `/ship` on `main`). Going from
  `feat/*` or `research/*` to `dev` is now a plain `gh pr create --base
  dev` (or `commit-commands:commit-push-pr`) — no ceremony, no gates,
  no per-subsystem tags. Methodology version tracking moves to the spec
  doc's frontmatter `version:` field, bumped in the same `feat/*` PR
  that lands the change. Projects that relied on `/promote` should
  update their `.claude/rules/git-workflow.md` and `methodology.md` to
  the single-namespace model. Historical `{alias}-vX.Y.Z` and
  `prod-{alias}-vX.Y.Z-YYYYMMDD` tags are preserved for archaeology;
  no new tags added in those namespaces.

## v1.14.0 (2026-05-09)

### Feat

- **qute-essentials**: /worktrees skill becomes config-driven via
  `.claude/worktree.json` (`base_path`, `branch_pattern`, `default_type`,
  `shared_dirs`, `copy_files`, `venv_setup`, `base_branch`) plus optional
  `.claude/post-worktree.sh` hook for project-specific custom setup.
  Projects with shared `data/`/`models/` dirs, custom venv layout, or
  out-of-repo worktree conventions (quant/ML monorepos) no longer need
  bespoke worktree-creation instructions in their own rules — the skill
  reads project config and applies symlinks, file copies, and uv/pip
  venv setup automatically. Worktree slug is intended to match the
  project's task-slug convention (`docs/tasks/{slug}.md`), so one
  identifier threads through branch / worktree dir / venv / Stop hook /
  handoff frontmatter. Backwards-compatible: projects without
  `worktree.json` get the prior in-repo `.worktrees/<branch>` default
  behavior.

## v1.12.0 (2026-05-01)

### Feat

- **qute-essentials**: /ship auto-wipes TASKS.md::Completed sections after
  cz bump succeeds. Work just shipped, the canonical record is in CHANGELOG.md;
  a follow-up `chore(tasks): wipe Completed after vX.Y.Z` commit lands on the
  same branch as the bump. Skipped silently if TASKS.md is missing.
- **qute-essentials**: /pickup auto-syncs local main to origin/main at the
  start of the audit (best-effort `git fetch origin main && git update-ref`).
  Prevents stale-local-main false alarms in `git tag --merged main` queries
  (the "orphan tag" misdiagnosis pattern). Skips silently on offline / no-remote.

## v1.11.0 (2026-05-01)

### Feat

- **qute-essentials**: /pickup + /promote surface stale alias-related branches.
  /pickup gains a "Stale branches" inventory bullet that scans `feat/*` and
  `research/*` refs, lists ahead/behind/age, and flags drift candidates
  (>14d stale or >20 commits behind). /promote gains a preflight scan
  (step 5) that surfaces orphan branches sharing the same alias before
  gates run, with a heuristic that picks up historical aliases from the
  Subsystems table prose. Closes the workflow gap where a LOCKED
  methodology spec sits parked on a `feat/{alias}-*` branch and gets
  left behind when a sibling release ships.
