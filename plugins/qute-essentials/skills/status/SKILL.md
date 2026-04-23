---
name: status
description: Print current production state for a subsystem (or all subsystems) — reads STATUS.md + git tags. Quick mid-session "what's in prod right now?" without the full /pickup handoff re-read. Use when the user asks "what's the current state", "what version is live", "what's deployed", or references a subsystem's state.
argument-hint: "[subsystem]"
---

# /status

Quick mid-session state query. Prints "In Production" info per subsystem from STATUS.md + the latest production tag.

Lightweight alternative to `/pickup` — no handoff processing, no drift check, just "what's live?".

## When to use

- Mid-session: "wait, what's actually in prod right now?"
- Before proposing a change: "is this already the way it works?"
- Before running a pipeline: "which version of the methodology should I expect?"
- User asks "status", "where are we", "what's live"

Do NOT invoke for:
- Session resumption (use `/pickup` — it handles handoff + drift)
- Writing state (use `/handoff` or direct edit of STATUS.md)

## Arguments

- `[subsystem]` (optional) — e.g. `taa`, `fundsel`. If given, report that subsystem only. If omitted, list all subsystems declared in `.claude/promote.config.yaml`.

## Behavior

1. **Load config**:
   - Read `.claude/promote.config.yaml`. If missing → fall back to scanning `research/*/STATUS.md` files directly.
   - Validate `<subsystem>` exists under `subsystems:` (if provided). If not → list known subsystems and stop.

2. **Per subsystem**, gather:
   - Latest production tag: `git tag --list 'prod-{slug}-*' | sort -V | tail -1`
   - Tag date (from git): `git log -1 --format=%ad --date=short <tag>`
   - STATUS.md content if `status_file` configured: read and extract "In Production" section
   - Spec frontmatter if `spec_file` configured: read version + date_locked + status

3. **Check freshness**:
   - STATUS.md mtime vs last commit touching `src_paths` on current branch
   - If STATUS.md is stale (older than a src/ commit), flag `⚠️ STATUS.md may be stale`

4. **Print compact report** (see Output Format).

## Output Format

### Single subsystem (`/status taa`)

```markdown
## taa (Tactical Signals)

**Production:** prod-taa-v3.0.0-20260408 (tagged 2026-04-08)
**Spec:** research/tactical-signals/docs/signal-definitions-v4.md — v4.5.0 LOCKED 2026-04-23
**Status file:** research/tactical-signals/STATUS.md (updated 2026-04-23 ✓ fresh)

### In Production (from STATUS.md)
<extracted content of "In Production" section>

### Spec sections
- §2 EQ_US: LOCKED 2026-04-21
- §3.5 FI v4.5: LOCKED 2026-04-23
- §4 Scoring v4.6: PROPOSED 2026-04-23

### Research locked, awaiting promotion
<extracted from Research Locked section — just the count + list of versions>
```

### All subsystems (`/status`)

```markdown
## Subsystem status overview

| Subsystem | Prod | Spec version | Status |
|---|---|---|---|
| taa | prod-taa-v3.0.0-20260408 | v4.5.0 LOCKED | Research ahead of prod (v4+) |
| fundsel | prod-fundsel-ml-v2.1.3-20260301 | — | No spec file |
| extract | prod-extract-v4.0.0-20260215 | — | No spec / no research dir |
```

## Conventions

- **Read-only** — never writes. Purely diagnostic.
- **Fast** — target under 2s. No git diff beyond tag lookup, no full handoff parsing.
- **Fail-soft** — if STATUS.md missing for a subsystem, just print "(no STATUS.md)". If no tag exists, print "(no prod tag yet)".
- **Compact output** — ~20 lines max for single subsystem, ~10 lines for overview.

## Example

```
/status taa
```

Reads `.claude/promote.config.yaml`, finds the `taa` subsystem config, looks up `prod-taa-*` tag, reads `research/tactical-signals/STATUS.md` + spec frontmatter, prints the compact report. 2 seconds.

## See also

- `/pickup` — full handoff + drift check at session start
- `/handoff` — end-of-session state write (pairs with /status as a quick-read counterpart)
- `/promote` — promotion workflow with gating (updates STATUS.md on success)
- `.claude/promote.config.yaml` — subsystem declarations
