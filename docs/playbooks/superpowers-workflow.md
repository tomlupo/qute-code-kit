# Superpowers Workflow

> Structured planning and execution via the superpowers plugin.

## When to Use

Starting a new feature with unclear requirements, need structured planning with bite-sized tasks, or want TDD-driven implementation.

## Flow

```
brainstorm → write-plan → execute-plan
     |            |             |
  clarify     detailed      run work
   idea        tasks       task-by-task
```

## Steps

### 1. Brainstorm

```
superpowers:brainstorming
```

Explore ideas, clarify requirements. Asks questions, considers approaches, applies YAGNI. Use before any creative work — features, components, refactors.

### 2. Write Plan

```
superpowers:writing-plans
```

Create bite-sized implementation plan from spec/requirements. Produces step-by-step tasks with clear acceptance criteria.

### 3. Execute Plan

Two execution modes:

**Sequential** (checkpoints between steps):
```
superpowers:executing-plans
```
Execute in separate session with review checkpoints at each step.

**Parallel** (fresh subagent per task):
```
superpowers:subagent-driven-development
```
Each task gets an isolated subagent — prevents context pollution between tasks.

## Supporting Skills

| Skill | When |
|-------|------|
| `superpowers:test-driven-development` | Before writing implementation code |
| `superpowers:systematic-debugging` | When encountering bugs or test failures |
| `superpowers:requesting-code-review` | Before merging, after implementation |
| `superpowers:using-git-worktrees` | For feature isolation |
| `superpowers:verification-before-completion` | Before claiming work is done |

## Combining with Compound Engineering

```
superpowers:brainstorming     → clarify what to build
/workflows:plan               → detailed plan with research
superpowers:subagent-driven   → execute with fresh agents
/workflows:review             → multi-agent review
/workflows:compound           → capture learnings
```

See `compound-engineering-workflow.md` for the compound side.
