---
name: worktrees
description: Guide for using git worktrees to parallelize development with coding agents. Use this skill when the user requests to work in a new worktree or wants to work on a separate feature in isolation (e.g., "Work in a new worktree", "Create a worktree for feature X").
argument-hint: "[slug]"
---

# Git Worktrees for Parallel Development

## Overview

This skill enables parallel development by using git worktrees. Each worktree provides an isolated working directory with its own branch, allowing multiple agents to work on different features simultaneously without conflicts.

The skill is **config-driven**: projects can customize worktree path, branch naming, and post-create setup via `.claude/worktree.json` and `.claude/post-worktree.sh`. With no config, sensible defaults apply (in-repo `.worktrees/<branch>`).

## When to Use This Skill

Use this skill when:
- User explicitly requests to work in a new worktree (e.g., "Work in a new worktree")
- User wants to develop a feature in isolation while preserving the main working directory
- Multiple agents need to work on different tasks in parallel

## Workflow

### 0. Read project config (optional)

Look for `.claude/worktree.json` in the project root. If present, parse:

| Key | Meaning | Default if absent |
|---|---|---|
| `base_path` | Template for worktree path. Supports `{project}` (= main checkout dir basename), `{slug}`, and `$HOME`. | `.worktrees/{slug}` (in repo) |
| `branch_pattern` | Template for branch name. Supports `{type}` and `{slug}`. | `{slug}` |
| `default_type` | Used when caller didn't specify a type (e.g. `feat`, `research`). | `feat` |
| `shared_dirs` | List of directory names to symlink from main checkout (e.g. `["data", "models", "output"]`). | `[]` |
| `copy_files` | List of file names to copy from main checkout (e.g. `["local.toml"]`). | `[]` |
| `venv_setup` | One of `uv`, `pip`, `none`. Drives post-create venv initialization. | `none` |
| `base_branch` | Branch to fork from. | `dev` if it exists, else `main` |

Example `.claude/worktree.json`:

```json
{
  "base_path": "$HOME/workspace/projects/.worktrees/{project}-{slug}",
  "branch_pattern": "{type}/{slug}",
  "default_type": "feat",
  "shared_dirs": ["data", "models", "output"],
  "copy_files": ["local.toml"],
  "venv_setup": "uv",
  "base_branch": "dev"
}
```

If no config file exists, defaults apply (in-repo `.worktrees/`, no symlinks, no venv setup).

### 1. Determine Slug + Branch

Choose a descriptive slug (lowercase, hyphen-separated, e.g., `add-user-authentication`, `fix-login-bug`). If the project uses task slugs (`docs/tasks/{slug}.md`), the worktree slug should match — this threads one identifier through branch / worktree dir / venv / Stop hook / handoff frontmatter.

Resolve the branch name from `branch_pattern` and the type (caller-specified or `default_type`).

### 2. Create Worktree

Resolve the worktree path from `base_path` (substitute `{project}`, `{slug}`, expand `$HOME`).

```bash
git worktree add <resolved-path> -b <branch-name> origin/<base_branch>
```

If `dev` exists locally or remotely, prefer it; otherwise fall back to `main`.

### 3. Switch to Worktree

```bash
cd <resolved-path>
```

### 4. Apply project shared resources (if configured)

After `cd`, if `worktree.json` is present:

- For each `shared_dirs` entry: if `$MAIN/$dir` exists, run `ln -sf "$MAIN/$dir" "$dir"` (replacing any auto-created empty dir).
- For each `copy_files` entry: if `$MAIN/$file` exists, run `cp "$MAIN/$file" .`.
- If `venv_setup == "uv"`:
  ```bash
  echo 'export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/${PWD##*/}"' > .envrc
  direnv allow 2>/dev/null || true
  uv sync
  ```
- If `venv_setup == "pip"`:
  ```bash
  python -m venv .venv && .venv/bin/pip install -e .
  ```
- If `venv_setup == "none"` or absent: skip.

`$MAIN` resolves to the main checkout directory (the original repo root, not the worktree).

### 5. Run post-create hook (optional)

If `.claude/post-worktree.sh` exists and is executable in the project, run it inside the new worktree. Surface non-zero exit as an error.

This is the escape hatch for project-specific custom setup beyond what config can express (e.g., starting services, running migrations, generating local secrets).

### 6. Work in Isolation

Proceed with development in the worktree. This environment is completely isolated from the main working directory; standard git operations (commit, push, pull) work normally.

**Project-type notes (when no `worktree.json` is present):**
- **Web apps / services** — if this project runs services (docker-compose, dev servers, database containers), check for port collisions with the main worktree. Use `scripts/allocate-ports.sh` (shipped with this skill) to allocate non-overlapping ports.
- **Quant / ML / data science** — large `data/` or `models/` directories benefit from symlinking via `shared_dirs` config. Set `venv_setup: "uv"` for per-worktree venv via `${PWD##*/}` keying.

### 7. List Active Worktrees (optional)

```bash
git worktree list
```

### 8. Remove Worktree (optional)

```bash
git worktree remove <path>
```

**Note:** Don't auto-remove worktrees. Leave the decision to the user. If services are running, stop them first via `scripts/shutdown-services.sh`. After removal, delete the branch separately (`git branch -d <name>`, or `-D` to force when squash-merged).

## Important Notes

- For **in-repo** worktree paths (`.worktrees/<branch>`), add `.worktrees/` to `.gitignore`. **Out-of-repo** paths (recommended for projects with recursive tooling like `rg`, IDE indexers, `git rev-parse --show-toplevel` consumers) avoid this concern entirely.
- Each worktree maintains its own working directory but shares the same git repository.
- After creating and switching to a worktree, inform the user of the new working directory path.

## Gotchas

- **`.worktrees/` must be in `.gitignore`** if using in-repo paths — otherwise `git status` shows worktree contents as untracked, polluting repo state.
- **Two worktrees cannot share a branch** — git refuses with "already checked out"; use a new branch name per worktree.
- **`git worktree remove` does not delete the branch** — delete separately with `git branch -d <branch>` (or `-D` to force; needed for squash-merged branches whose tip commits aren't in the base branch's history).
- **Database migrations conflict** if worktrees share a dev database — use separate databases or stop one before migrating.
- **Venv first-time setup is not free** — `uv sync` from cache is typically 10-30s. Per-worktree venvs avoid cross-branch dep conflicts but cost initialization time.
- **Removing a worktree with uncommitted changes fails** — stash, commit, or discard first.
- **Symlink replaces auto-created empty dir** — `git worktree add` creates the worktree with copies of all tracked-in-the-repo dirs (empty if untracked-but-present in `.gitignore`). Symlinking via `shared_dirs` requires `ln -sf`, not just `ln -s`, to overwrite the empty dir.
