---
name: status
description: Print per-subsystem prod/dev tags, active worktrees, TASKS.md::Now items, and orphan handoff warnings. Pure bash, no LLM, sub-second. Use when user says "status", "where are we", "what's live", "what version is in prod", or names a subsystem.
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
- `$CLAUDE_PROJECT_DIR/CLAUDE.md` Subsystems table (alias list)
- `git tag` namespaces matching `{alias}-v*`
- `git worktree list`
- `TASKS.md::Now`
- `.claude/handoffs/*.md` (orphan detection)

The skill MUST NOT call other skills, write files, or perform LLM synthesis.

## Output anatomy

```
{project} @ {branch}{dirty?}  ·  {last commit hash + subject}

Subsystem    Prod (main)            Dev                    Active
  taa        taa-v4.8.1             taa-v5.1.0             research/taa-v6-...
  selection  fundsel-v1.0.0         =                      —
  ...

Worktrees (3):
  dm-evo                            [dev]
  dm-evo-taa                        [research/taa-v6-...]
  ...

Now (TASKS.md):
  TAA v6.0.0 — engine ship ...
  Validate FI_PL_SHORT widening ...

Orphan handoffs (no TASKS.md link):
  2026-05-XX-some-handoff.md (task: foo — not in TASKS.md, status: in-progress)
```

Sections that are empty (no orphans, no Now items) are silently dropped.

## Notes

Per DR-010, this skill no longer reads `STATUS.md`. Subsystem state is regenerated from git tags and worktree state on every invocation — single source of truth, never stale.

Known gap: aliases whose tag namespace differs from the alias name (e.g. `selection` → legacy `prod-fundsel-*`) show blank `Prod (main)` until first promote in the new namespace. Future enhancement: optional `legacy_alias` field in CLAUDE.md::Subsystems.
