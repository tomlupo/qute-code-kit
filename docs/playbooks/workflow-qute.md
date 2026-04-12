# qute-essentials Dev Session Workflow

> Full dev session lifecycle — from picking up work to shipping and handing off — using qute-essentials skills end-to-end.

## Overview

```
/pickup → work → /test → /decision → /gbu → /ship → /handoff
              ↑                                           ↓
         guards run silently                      next session starts
         (secrets, destructive,                   here with /pickup
          malware, lakera, audit)
```

## Skills Used

| Skill | When | What it does |
|-------|------|--------------|
| `/pickup` | Session start | Load last handoff, verify ADRs, summarise TASKS.md |
| `/worktrees` | Before parallel work | Isolate feature in a git worktree |
| `/decision` | When a design choice is locked | Record ADR with auto-numbering |
| `/test` | After code changes | Run suite, group failures by root cause, propose fixes |
| `/gbu` | Before committing | Good/Bad/Ugly self-review |
| `/ship-setup` | Once per project | Add commitizen + CHANGELOG |
| `/ship` | Ready to release | Bump version, update CHANGELOG, create tag |
| `/handoff` | Session end | Capture context, ADRs touched, TASKS snapshot |

Guards run automatically in the background — no invocation needed.

## Step-by-step

### 1. Start: `/pickup`

```
/pickup
```

Reads the latest `.claude/handoffs/*.md`, checks that referenced ADRs are still `Accepted` (not superseded), prints TASKS.md Now/Next, and flags any stale handoffs. Read-only.

If no handoff exists: read TASKS.md directly and start from Now.

---

### 2. Work (guards run silently)

Code normally. The following hooks fire automatically:

| Hook | Trigger | Effect |
|------|---------|--------|
| `secrets-guard` | Write/Edit | Blocks API key / credential leaks |
| `destructive-guard` | Bash | Blocks `rm -rf`, `git reset --hard`, etc. |
| `malware-scan` | Write/Edit | Blocks obfuscated code or crypto drainers |
| `format_python` | Write/Edit .py | Auto-ruff-formats on save |
| `auto_audit` | After `uv add` / `pip install` | Runs pip-audit, reports CVEs |
| `doc_reminder` | Write/Edit | Reminds to record decisions when editing decision-adjacent files |
| `lakera` / `langfuse` | PostToolUse | Injection screening + tracing (if API keys set) |

To check or toggle any guard: `/guard` or `/guard <name> off`.

---

### 3. Record decisions: `/decision`

When a non-trivial design choice is locked in:

```
/decision "use rolling 252-day window for volatility normalisation"
/decision "migrate from sqlite to postgres" --supersedes 0003
```

Creates `docs/decisions/NNNN-slug.md`. The `/handoff` at session end auto-links to every ADR touched this session.

---

### 4. Test: `/test`

```
/test                    # full suite
/test test_pricing       # filtered
```

Detects pytest/jest/cargo/go test. Groups failures by root cause. Proposes the minimal fix per group — does not apply without confirmation.

---

### 5. Review: `/gbu`

Before committing a substantial change:

```
/gbu
```

Good/Bad/Ugly structured review. Surfaces real issues without nitpicking style — use the Bad/Ugly findings to decide what to fix before shipping.

---

### 6. Commit

```
/commit
```

Generates a conventional commit message from staged changes (`feat:`, `fix:`, `docs:`, etc.).

---

### 7. Release: `/ship` (Python projects)

One-time setup (run once per project):

```
/ship-setup
```

Adds commitizen as a dev dependency, initialises CHANGELOG.md, creates `.github/workflows/release.yml`.

When ready to release:

```
/ship
```

Reads conventional commits since last tag, bumps version in `pyproject.toml`, updates CHANGELOG.md, creates a git tag. PATCH is automatic; MINOR/MAJOR asks once.

---

### 8. End: `/handoff`

```
/handoff "finishing rate-limiting endpoint"
/handoff --push           # also pushes the handoff branch
```

Creates `.claude/handoffs/YYYY-MM-DD-slug.md` capturing:
- What was done and what remains
- ADRs recorded or superseded this session
- TASKS.md snapshot (Now/Next/Later/Done)
- Git state (branch, uncommitted files)
- Blockers needing user action
- Exact next steps for the next session

---

## Quick reference

```
/pickup          ← start here
  ... work ...
/decision "X"    ← when a choice is made
/test            ← verify nothing broke
/gbu             ← review before committing
/ship            ← cut a release
/handoff         ← end here
```

## See also

- `session-continuity.md` — focused guide on the handoff/pickup pair
- `workflow-gstack.md` — alternative ship workflow using gstack (richer: test triage, coverage, PR creation)
- `superpowers-workflow.md` — structured planning before starting a feature
- `compound-engineering-workflow.md` — multi-agent review and knowledge capture after shipping
