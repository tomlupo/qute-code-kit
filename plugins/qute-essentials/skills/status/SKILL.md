---
name: status
description: Print current per-subsystem and repo-train versions from git tags + root STATUS.md. Quick mid-session "what's where right now?" without the full /pickup handoff re-read. Two version axes — release train (`vX.Y.Z` on main) and per-subsystem models (`{alias}-vX.Y.Z`). Use when the user says "status", "what's live", "what version is in prod", "where are we", or names a subsystem.
argument-hint: "[alias]"
---

# /status

Quick mid-session state query. Prints repo-train version + per-subsystem model versions from git tags, plus the root `STATUS.md` Notes block.

Lightweight alternative to `/pickup` — no handoff read, no drift check, no audits. Just "what's where?".

## When to use

- Mid-session: "wait, what's actually in prod right now?"
- Before proposing a change: "is this already the way it works?"
- User says "status", "where are we", "what's live", "current version"

Do NOT invoke for:
- Session resume — use `/pickup` (handoff + audits)
- Writing state — use `/handoff`

## Arguments

- `[alias]` (optional) — short alias (`taa`, `selection`) or subsystem dir name (`tactical-signals`). If given, report only that subsystem. If omitted, list all.

## Behavior

1. **Resolve subsystem list (no config file):**
   - If `[alias]` is given, treat it as the only subsystem and skip discovery. Resolve to a dir under `research/` if such a dir exists; otherwise treat the alias literally.
   - Otherwise, discover subsystems from git tag namespaces: every distinct prefix in `git tag --list '*-v*'` matching `{alias}-vX.Y.Z` is a candidate. Augment with directories under `research/` that have a `docs/` subdirectory. Union of both.
   - The project's `/CLAUDE.md::Subsystems` table is reference documentation — do not parse it. Filesystem + tags are the source of truth.

2. **Per subsystem, gather (one alias = one row):**
   - Latest subsystem tag: `git tag --list '{alias}-v*' | sort -V | tail -1`
   - Legacy tag (informational only): `git tag --list 'prod-{alias}-*' | sort -V | tail -1` — show in a "(legacy)" suffix if newer-or-only-tag is the legacy one.
   - In-prod check: `git merge-base --is-ancestor {tag} main` — flag whether the latest subsystem tag is reachable from `main`.
   - Latest LOCKED spec under `research/{subsystem}/docs/*.md` (parse YAML frontmatter, take highest `version` with `status: LOCKED`). Print version + `date_locked`.

3. **Repo-train version:**
   - `git tag --list 'v*' | sort -V | tail -1` — latest release train tag (set by `/ship` on `main`).
   - `pyproject.toml::version` (if it exists) — flag if it differs from the latest tag (means a `/ship` is queued).

4. **Root STATUS.md (single source of truth):**
   - Read root `STATUS.md` if present. Echo its `## Notes` section verbatim (capped at ~15 lines).
   - If absent, skip silently.

5. **Print compact report.** No drift checks, no diff. Target under 1s wall time.

## Output Format

### Single subsystem (`/status taa`)

```markdown
## taa (tactical-signals)

**Latest tag:**   taa-v5.1.0  (in prod ✓)            tagged 2026-04-30
**Spec:**         signal-definitions-v51.md  v5.1.0 LOCKED 2026-04-30
**Legacy:**       prod-taa-v4.8.1-20260427  (informational)
```

### All subsystems (`/status`)

```markdown
## dm-evo — status

**Release train:** v0.4.0 on main         (pyproject.toml: 0.4.0 ✓)

| Alias       | Latest tag       | In prod | Spec         | Notes |
|---|---|---|---|---|
| taa         | taa-v5.1.0       | ✓       | v5.1.0 LOCKED | — |
| selection   | (none)           | —       | (no LOCKED spec) | — |
| extract     | (no tag)         | —       | (no spec) | direct feat→dev→ship |
| app         | (no tag)         | —       | (no spec) | direct feat→dev→ship |

### Notes (from root STATUS.md)
<echo of ## Notes block, capped at 15 lines>
```

## Conventions

- **Read-only** — never writes.
- **Fast** — under 1s. No `git diff`, no full repo scan, no YAML config parse. The skill's whole job is "what do tags + frontmatter + STATUS.md say right now?".
- **Fail-soft** — missing `STATUS.md` → omit Notes section. No tags for a subsystem → `(no tag)`. No spec → `(no spec)`. Never block the report on missing optional files.
- **Compact** — single subsystem ~5 lines, overview ~10 lines + Notes block.

## Example

```
/status taa
```

Resolves `taa` (alias matches `research/tactical-signals/`), looks up latest `taa-v*` tag and the highest LOCKED spec under `research/tactical-signals/docs/`, prints the compact report. Sub-second.

## See also

- `/pickup` — full session resume with handoff + audits (use this at session start)
- `/promote {alias}` — per-subsystem promotion (`{alias}-vX.Y.Z` on `dev`)
- `/ship` — repo release train (`vX.Y.Z` on `main`)
- Root `STATUS.md` — single dashboard; per-subsystem STATUS.md files no longer exist
