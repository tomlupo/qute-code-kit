---
name: project-seed
description: "Seed a new repo from Obsidian vault specs. Creates CLAUDE.md, AGENTS.md, TASKS.md, docs structure, and copies specs from vault. Use when starting a new project or setting up an existing repo for agent-driven development."
user-invocable: true
---

# Project Seed

Set up a repo for agent-driven development by pulling context from the Obsidian vault.

## Prerequisites

- Vault accessible locally (use `vault-access` skill to resolve path)
- Git repo initialized (or will create one)
- Know the vault project path (e.g., `projects/alphaops/collaboo/`)

## Step 1: Read vault context

Use the `vault-access` skill to resolve the vault path. Then read:

1. `_meta.md` — get `github_repo`, `project_dir`, `status`
2. List all `.md` files in the project folder — these are the specs to copy
3. Read each spec to understand the project

## Step 2: Create repo structure

```bash
mkdir -p docs/specs docs/architecture docs/decisions .claude/skills/vault-access
```

## Step 3: Copy and classify specs

Copy vault specs into the repo, classifying by type:

| If spec is about... | Copy to |
|---------------------|---------|
| Product requirements, problem, users, decisions | `docs/specs/` |
| User flows, journeys, scenarios | `docs/specs/` |
| Data model, ERD, schemas | `docs/architecture/` |
| Technical architecture, stack, structure | `docs/architecture/` |
| Competitive analysis, market research | `docs/specs/` |

**Translate to English** if the source is in another language. Keep technical terms, translate prose.

Rename files to English kebab-case (e.g., `koncepcja-produktu.md` → `prd.md`).

## Step 4: Generate CLAUDE.md

Create `CLAUDE.md` with these sections:

```markdown
# {Project Name}

{One-line description from _meta.md}

## Stack
- (determine from specs or ask user)

## Docs
| Doc | Path | Purpose |
|-----|------|---------|
(list all docs in specs/ and architecture/)

Live source: Obsidian vault `{vault project path}`.
Use `/vault-access` skill to fetch latest.

## How to run
(fill in once scaffolded, or leave as TODO)

## Conventions
(determine from stack or ask user)

## Key domain concepts
(extract from PRD / data model — the 5-8 core entities)

## Protected paths
- `alembic/versions/` or equivalent migrations
- `.github/workflows/`
- Auth/secrets configuration

## Phase plan
(extract from PRD if phased)
```

## Step 5: Create supporting files

### AGENTS.md
```markdown
# Agents

See [CLAUDE.md](CLAUDE.md) for all project instructions and conventions.
```

### TASKS.md
Break the project into ordered, PR-sized tasks. Each task needs:
- Title
- Subtask checkboxes
- "Done when" acceptance criteria

Read the specs to determine the right task ordering.

### docs/decisions/000-template.md
Copy from `templates/docs/adr-template.md`.

### docs/progress.md
```markdown
# Progress Log

## Codebase Patterns
(consolidate reusable patterns here)

---
<!-- Append new entries below -->
```

### .claude/skills/vault-access/SKILL.md
Copy from `claude/skills/vault-access/SKILL.md`. Update hostname mapping if needed.

### .gitignore
Standard ignores for the project's stack.

## Step 6: Commit and push

```bash
git add -A
git commit -m "feat: seed project from vault specs"
git push -u origin main
```

## Step 7: Verify

Confirm the agent can work autonomously:
- [ ] CLAUDE.md describes the project clearly
- [ ] TASKS.md has ordered tasks with acceptance criteria
- [ ] docs/specs/ has the product specs in English
- [ ] docs/architecture/ has technical specs
- [ ] vault-access skill has correct hostname mapping
- [ ] .gitignore covers the stack's artifacts
