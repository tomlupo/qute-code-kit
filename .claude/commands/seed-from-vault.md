---
description: "Seed a repo from Obsidian vault specs. Creates CLAUDE.md, AGENTS.md, TASKS.md, docs structure, copies and translates specs."
---

Use the `project-seed` skill to set up this repo for agent-driven development.

Read the vault project path from the user (e.g., `projects/alphaops/collaboo/`), then follow the skill's steps to:

1. Read `_meta.md` and all specs from the vault
2. Create docs structure (specs/, architecture/, decisions/)
3. Copy and translate specs to English
4. Generate CLAUDE.md with project context
5. Create AGENTS.md, TASKS.md, progress.md
6. Set up vault-access skill
7. Commit everything

$ARGUMENTS should be the vault project path. If not provided, ask the user.
