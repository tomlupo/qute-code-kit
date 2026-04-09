# Git Workflow

## Branch Strategy

| Branch | Purpose | Merge Target |
|--------|---------|--------------|
| `main` | Production-ready code | — (deploy target) |
| `dev` | Integration + working branch | `main` via PR |
| `feat/*` | Feature development, branched from `dev` | `dev` via PR or merge |

Standard flow: `feat/xyz` → merge to `dev` → PR `dev` to `main`.

**Development happens on `feat/*` branches, not directly on `dev`.** This keeps `dev` clean for PRing to main. When a `dev → main` PR is open, any push to `dev` auto-updates it — so only merge finished `feat/*` work into `dev` before creating the PR.

## Research Code Policy

**Research and experiments live on `dev` in `research/` directories — NOT on separate branches.**

### Why not separate research branches

1. **Directory isolation is sufficient** — `research/selection/`, `research/autoresearch-*/`, `research/{study-name}/` already isolate exploration from production code.
2. **Shared infrastructure must stay in sync** — modules like `research/selection/wf_contract.py` are imported by production pipelines. A research-only branch would fork this shared code.
3. **Research branches drift and go stale** — team members can't discover exploration work if it's hidden on long-lived branches.
4. **Findings are documentation** — `FINDINGS.md`, experiment results, and baseline numbers are reference material that belongs on mainline.

### Production promotion of research findings

When a research experiment produces a winning configuration and is ready to be adopted in production:

```
dev  (has research exploration)
  │
  └─ feat/ml-{specific-change}
      ├─ Modify production config (e.g., config/fund-selection/scoring.yaml)
      ├─ Run production validation (e.g., research/selection/ml_train.py)
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
| Data fix | "fix: default mainunit=1 for 302 unclassified FIO PLN funds" |
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
