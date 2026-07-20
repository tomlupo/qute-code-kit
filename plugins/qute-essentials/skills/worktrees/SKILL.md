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

### 4. Apply project setup (shared dirs, copied files, venv, post-create hook)

Run the shared setup implementation — the same script the plugin's native
`WorktreeCreate` hook uses, so the skill path and `claude --worktree` cannot
diverge:

```bash
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/hooks/worktree_create.py --setup <resolved-path> --base <main-checkout>
```

It applies `worktree.json` (`shared_dirs` symlinks, `copy_files`,
`venv_setup`) and then `.claude/post-worktree.sh` if executable. It **fails
loudly**: a non-zero exit means setup did NOT complete (e.g. `uv` missing,
`uv sync` failed, post-worktree.sh errored) — report the error to the user,
do not proceed as if setup succeeded.

What it does for each `venv_setup` value (for reference):

- `"uv"`: writes `.envrc` exporting
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/${PWD##*/}"`, runs `direnv allow`
  (best-effort), then `uv sync` — and verifies the venv actually exists.
- `"pip"`: `python -m venv .venv && .venv/bin/pip install -e .`
- `"none"`/absent: venv skipped; `shared_dirs`/`copy_files` still apply.

### 5. Native path convergence

When this plugin is installed, native worktree creation (`claude --worktree`,
subagent `isolation: "worktree"`) runs the exact same setup automatically via
the `WorktreeCreate` hook in `hooks/hooks.json` — no skill invocation needed.
The skill remains the interactive/config-aware path (custom `base_path`,
`branch_pattern`, base-branch choice); both call `worktree_create.py` for
setup.

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
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/hooks/worktree_remove.py --reap <path>
```

The second command reaps the per-worktree venv (`$HOME/.venvs/<dir-basename>`)
that `venv_setup: "uv"` created — without it, removed worktrees leak venvs
forever. It is defensive by design: it refuses (with a logged reason, see
`~/.claude/qute-worktree-reap.log`) unless the target is a real, unused venv
strictly inside `$HOME/.venvs/` carrying the `.qute-worktree.json` ownership
marker (stamped at setup time) that names this exact worktree — legacy venvs
without a marker are left alone. Native worktree removal triggers the same
reap automatically via the `WorktreeRemove` hook.

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
