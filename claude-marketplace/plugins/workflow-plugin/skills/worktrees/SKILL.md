---
name: worktrees
description: Guide for using git worktrees to parallelize development with coding agents. Use this skill when the user requests to work in a new worktree or wants to work on a separate feature in isolation (e.g., "Work in a new worktree", "Create a worktree for feature X").
---

# Git Worktrees for Parallel Development

## Overview

This skill enables parallel development by using git worktrees. Each worktree provides an isolated working directory with its own branch, allowing multiple agents to work on different features simultaneously without conflicts.

## When to Use This Skill

Use this skill when:
- User explicitly requests to work in a new worktree
- User wants to develop a feature in isolation while preserving the main working directory
- Multiple agents need to work on different tasks in parallel

## Workflow

### 1. Determine Branch Name

Choose a descriptive branch name for the feature or task. Follow standard git naming conventions (lowercase, hyphen-separated, e.g., `add-user-authentication`, `fix-login-bug`).

### 2. Create Worktree

Create a new worktree in the `.worktrees/` directory:

```bash
git worktree add .worktrees/<branch-name> -b <branch-name>
```

This command:
- Creates a new directory at `.worktrees/<branch-name>`
- Creates and checks out a new branch named `<branch-name>`
- Links the worktree to the current repository

### 3. Switch to Worktree

Change the working directory to the newly created worktree:

```bash
cd .worktrees/<branch-name>
```

### 4. Work in Isolation

Proceed with development tasks in the worktree. This environment is completely isolated from the main working directory.

All standard git operations (commit, push, pull, etc.) work normally within the worktree.

### 5. List Active Worktrees

To view all active worktrees:

```bash
git worktree list
```

### 6. Remove Worktree (User Decision)

When done with a worktree:

```bash
git worktree remove .worktrees/<branch-name>
```

**Note:** Don't automatically remove worktrees. Leave that decision to the user.

## Integration with Workflow System

Each worktree can have its own:
- Session (via `/workflow:session`)
- Ledger context
- Task tracking

This enables true parallel development:
- Main directory: Agent A works on feature X
- Worktree 1: Agent B works on feature Y
- Worktree 2: Agent C works on bugfix Z

## Important Notes

- The `.worktrees/` directory should be in `.gitignore`
- Each worktree shares the same git repository but has independent working directories
- After creating a worktree, inform the user of the new working directory path
