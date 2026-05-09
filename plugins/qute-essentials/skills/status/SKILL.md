---
name: status
description: Print latest release tag, per-subsystem last change, active worktrees, TASKS.md::Now items, and orphan handoff warnings. Pure bash, no LLM, sub-second. Use when user says "status", "where are we", "what's live", "what changed in {subsystem}", or names a subsystem.
argument-hint: "[alias]"
---

# /status

Sub-second lifecycle dashboard. **No LLM body** — exec the bash script and print stdout verbatim.

## When to use

- Mid-session: "wait, what's actually in prod right now?"
- Before proposing a change: "is this already the way it works?"
- User says "status", "where are we", "what's live", or names a subsystem.

Do NOT invoke for:
- Session resume — use `/pickup` (loads handoff context into LLM).
- Writing state — use `/handoff`.

## Arguments

- `[alias]` (optional) — restrict report to a single subsystem (`taa`, `selection`, etc.). If omitted, list all subsystems found in `CLAUDE.md::Subsystems`.

## Behavior

Single bash invocation:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/lifecycle/status.sh" $1
```

If `$CLAUDE_PLUGIN_ROOT` is unset, fall back to a skill-relative path:
```bash
bash "$(dirname "$0")/../../scripts/lifecycle/status.sh" $1
```

Print stdout verbatim. Surface non-zero exit as a warning.

The script reads:
- `$CLAUDE_PROJECT_DIR/CLAUDE.md` Subsystems table (alias + production paths from column 3)
- `git tag --list 'v*'` (latest release tag, single namespace)
- `git log --first-parent -1 -- {subsystem-paths}` (last change per subsystem)
- `git worktree list`
- `TASKS.md::Now`
- `.claude/handoffs/*.md` (orphan detection)

The skill MUST NOT call other skills, write files, or perform LLM synthesis.

## Output anatomy

```
{project} @ {branch}{dirty?}  ·  {last commit}
Latest release: vX.Y.Z (YYYY-MM-DD)  ·  N commits ahead on dev

Subsystem    Last change                                       Active branch
  taa        2026-04-29 b12a6a0 docs(taa): mark v6/v7 super...  research/taa-v6
  selection  2026-05-08 d496308 fix(selection): fund_master ... feat/selection-aum
  saa        (research-only)                                    —
  extract    2026-05-07 abc1234 feat(extract): santander Q1 ... —
  app        2026-04-15 def5678 feat(app): allocator UI         —

Worktrees (3):
  dm-evo                            [dev]
  dm-evo-taa-v6                     [research/taa-v6]
  dm-evo-fundsel-aum-flags          [feat/selection-aum-flags]

Now (TASKS.md):
  TAA v6.0.0 — engine ship
  Validate FI_PL_SHORT widening

Orphan handoffs (no TASKS.md link):
  2026-05-XX-some-handoff.md (task: foo — not in TASKS.md, status: in-progress)
```

Sections that are empty (no orphans, no Now items, no subsystems registry) are silently dropped.

## Notes

Per DR-010, this skill no longer reads `STATUS.md`. Per the single-namespace migration, this skill no longer queries `{alias}-vX.Y.Z` tags (retired alongside `/promote`). Subsystem-level "what's in prod?" is regenerated from `git log` against the production paths declared in column 3 of `CLAUDE.md::Subsystems`.

**Production paths parsing:** column 3 of the Subsystems table is parsed for backticked path tokens containing `/` (e.g. `` `src/taa_signals/` ``). Rows whose column 3 starts with `(` (parenthesized prose like `(research-only — ...)`) are treated as having no production paths and report `(research-only)` for last change.
