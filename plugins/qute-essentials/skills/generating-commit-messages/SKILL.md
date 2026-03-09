---
name: generating-commit-messages
description: |
  MANDATORY for ALL commits. Generates conventional commit messages and updates CHANGELOG.md
  on main branch. Triggers: before any "git commit", "commit changes", "commit this".
---

# Commit Messages

## Process

Before every `git commit`:

1. Run `git diff --staged` to review changes
2. Generate a message following the format below
3. If on `main` branch, update CHANGELOG.md after commit

## Conventional Commits Format

```
<type>: <summary under 50 chars>

<body: what changed and why>
```

### Types

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `docs` | Documentation only |
| `chore` | Build, deps, config, tooling |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `style` | Formatting, no code change |

### Rules

- Present tense imperative ("Add feature" not "Added feature")
- Summary under 50 characters
- Body explains **why**, not just what
- Be specific about affected components
- Never include "Generated with Claude Code" or "Co-Authored-By" lines

### Example

```
feat: Add multi-source data routing for market-datasets

Auto-routes ticker requests to best provider based on market:
- Polish equities → Stooq
- US equities → Yahoo Finance
- Crypto → Binance via CCXT
- Macro → FRED

Eliminates manual source selection for common data fetches.
```

## Changelog Update (main branch only)

After committing to `main`, check if CHANGELOG.md needs updating.

**Update for**: `feat`, `fix`, `perf`, breaking changes
**Skip for**: `refactor`, `chore`, `docs`, `test`, `style`

### Format

```markdown
## [YYYY-MM-DD]

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Breaking or notable behavior changes
```

Follow [Keep a Changelog](https://keepachangelog.com) conventions. Most recent entry at top.
