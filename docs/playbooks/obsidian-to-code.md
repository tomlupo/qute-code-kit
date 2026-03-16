# Playbook: Obsidian to Code

End-to-end workflow for going from product thinking in Obsidian to autonomous agent development.

## Overview

```
Obsidian (thinking) → Seed repo (docs) → Spec-kit (refine) → Ralph (execute) → Review
```

## Phase 1: Think in Obsidian

Work in your vault's `projects/` folder. Create notes, brainstorm, write specs.

### Required: `_meta.md`

Every project folder needs a `_meta.md` with frontmatter linking to external systems:

```yaml
---
project: my-project
github_repo: owner/my-project
status: active                    # draft | active | done | archived
tags: [dev, app]
project_dir: user@host:/path/to/working/dir
---

One-line description of the project.
```

- `project_dir` uses `user@host:path` format — update when you move dev to a different machine
- `status` tracks the project lifecycle
- Body is one paragraph max — this file is metadata, not documentation

### Spec docs in the same folder

Write these alongside `_meta.md`:

| Doc | Purpose | When to write |
|-----|---------|---------------|
| PRD | Problem, solution, users, key decisions | Before anything else |
| User flows | Step-by-step flows per actor | When UX matters |
| Data model | ERD, enums, schemas | When there's a database |
| Competitive analysis | Market positioning | When building a product |

Write in whatever language is natural. Translate to English when seeding the repo.

## Phase 2: Seed the repo

Use the `/seed-from-vault` command or do it manually:

### 2a. Create GitHub repo

```bash
gh repo create owner/my-project --private --clone
cd my-project
```

### 2b. Copy and translate specs

```bash
mkdir -p docs/specs docs/architecture docs/decisions
```

Copy vault specs into the repo:
- Product specs → `docs/specs/` (PRD, user flows)
- Technical specs → `docs/architecture/` (data model, tech spec)
- Translate to English if needed — agents work better in English

### 2c. Create founding docs

| File | Template | Purpose |
|------|----------|---------|
| `CLAUDE.md` | `project-templates/fullstack/CLAUDE.md` | Agent instructions — stack, conventions, vault refs |
| `AGENTS.md` | `project-templates/fullstack/AGENTS.md` | Pointer to CLAUDE.md |
| `TASKS.md` | `project-templates/fullstack/TASKS.md` | Ordered backlog with "done when" criteria |
| `docs/decisions/000-template.md` | `templates/docs/adr-template.md` | ADR template |
| `docs/progress.md` | (see template) | Running log for agent memory |
| `.gitignore` | `project-templates/fullstack/.gitignore` | Standard ignores |

### 2d. Add vault-access skill

```bash
mkdir -p .claude/skills/vault-access
cp <kit>/claude/skills/vault-access/SKILL.md .claude/skills/vault-access/
```

Edit the hostname→path mapping for your machines.

### 2e. Initial commit

```bash
git add -A && git commit -m "feat: seed project from vault specs"
git push -u origin main
```

## Phase 3: Refine with Spec-kit (optional)

For larger projects, use spec-kit to structure the specs further:

```bash
# Install spec-kit
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Initialize in project
specify init . --ai claude

# Establish development principles
/speckit.constitution

# Generate detailed specification from PRD
/speckit.specify   # feed it docs/specs/prd.md

# Generate implementation plan
/speckit.plan      # feed it docs/architecture/tech-spec.md
```

This adds `.claude/commands/speckit.*` slash commands available in all future sessions.

## Phase 4: Develop

Three modes, use whichever fits:

### Human + AI (interactive)

Open the repo in Claude Code, Cursor, or similar. Work through TASKS.md items interactively. Agent reads CLAUDE.md, knows the project, has vault access via skill.

### Ralph loop (autonomous)

```bash
# Install Ralph
# Generate stories from your plan
# Ralph creates prd.json with stories + acceptance criteria

# Run the loop
./ralph.sh
```

Ralph picks stories in priority order, implements, tests, commits. Each story = one commit.

### OpenClaw ACP (remote autonomous)

File a GitHub Issue with `job:queued` + `agent:coder` labels. OpenClaw cron detects it, dispatches via ACP to Claude Code / Codex. Agent works in the repo, creates PR.

## Phase 5: Review

### After each milestone

```bash
/speckit.review    # validates implementation against spec
```

### Continuous

- Agents append to `docs/progress.md` after each task
- ADRs in `docs/decisions/` capture non-obvious choices
- `docs/progress.md` "Codebase Patterns" section consolidates learnings

## File Map

```
project/
├── CLAUDE.md                          ← agent instructions (source of truth)
├── AGENTS.md                          ← pointer to CLAUDE.md
├── TASKS.md                           ← human-readable backlog
├── .claude/skills/vault-access/SKILL.md
├── docs/
│   ├── specs/                         ← what to build (product intent)
│   │   ├── prd.md
│   │   └── user-flows.md
│   ├── architecture/                  ← how to build it (technical)
│   │   ├── data-model.md
│   │   └── tech-spec.md
│   ├── decisions/                     ← why this way (ADRs)
│   │   └── 001-*.md
│   └── progress.md                    ← running log + codebase patterns
├── prd.json                           ← Ralph stories (auto-generated)
└── progress.txt                       ← Ralph execution log
```

## Tips

- **Start small.** Seed with PRD + TASKS.md. Add architecture docs when complexity demands it.
- **Translate specs.** Agents work better with English docs even if you think in another language.
- **One task = one PR.** Keep TASKS.md items scoped to single commits/PRs.
- **Let agents discover patterns.** The `progress.md` "Codebase Patterns" section builds institutional knowledge.
- **Review at milestones, not every commit.** Trust the spec, verify at phase boundaries.
