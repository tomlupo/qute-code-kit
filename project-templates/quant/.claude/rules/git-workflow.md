# Git Workflow

## Branch Strategy

| Branch | Purpose | Merge Target |
|--------|---------|--------------|
| `main` | Production-ready code | — (deploy target) |
| `dev` | Integration + research exploration | `main` via PR |
| `feat/*` | Specific feature or production change with validation | `dev` via PR |

Standard flow: `feat/xyz` → `dev` → `main`.

## Research Code Policy

**Research and experiments live on `dev` in `research/` directories — NOT on separate branches.**

### Why not separate research branches

1. **Directory isolation is sufficient** — `research/{study-name}/` already isolates exploration from production code.
2. **Shared infrastructure must stay in sync** — research modules imported by production pipelines would fork on a separate branch.
3. **Research branches drift and go stale** — team members can't discover exploration work if it's hidden on long-lived branches.
4. **Findings are documentation** — `FINDINGS.md`, experiment results, and baseline numbers are reference material that belongs on mainline.

### Production promotion of research findings

When a research experiment produces a winning configuration:

```
dev  (has research exploration)
  │
  └─ feat/{specific-change}
      ├─ Modify production config
      ├─ Run production validation
      ├─ Verify quality gates pass
      ├─ PR to dev
      └─ Merge dev → main
```

Each production promotion gets its own `feat/` branch with validation, never directly on dev.

## Commit Hygiene

- Create new commits, don't amend published ones
- Stage specific files (`git add path/to/file`), avoid `git add -A` or `git add .`
- Never skip hooks (`--no-verify`) unless explicitly requested
- Never force-push to `main` or `dev`
- Don't commit `.env`, credentials, or other secrets
- Don't auto-commit — only commit when explicitly asked

## Logical Commit Separation

Split unrelated changes into separate commits:

| Commit Type | Example |
|-------------|---------|
| Infrastructure | "research: shared wf_contract for ML fund selection" |
| Experiments | "research: autoresearch experiments + findings" |
| Data fix | "fix: default mainunit=1 for 302 unclassified funds" |
| Chore | "chore: add 7-day exclude-newer for supply chain safety" |

## Commit Message Conventions

Use prefixes to signal intent:
- `research:` — experiments, findings, exploratory code
- `feat:` — new production feature
- `fix:` — bug fix
- `refactor:` — restructuring without behavior change
- `docs:` — documentation only
- `chore:` — tooling, dependencies, config
- `test:` — test additions/changes

Message body explains **why**, not **what** (the diff shows what).

## Never Commit

- Files in `scratch/` (gitignored)
- Large binary outputs — save to `output/` (often gitignored) or DVC
- Credentials, tokens, `.env` files
- Personal editor/IDE configs beyond `.vscode/settings.json`
