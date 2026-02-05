# Planning Workflows Comparison

Two complementary workflow systems for structured development.

## Overview

| Aspect | Superpowers | Compound Engineering |
|--------|-------------|---------------------|
| **Source** | claude-plugins-official | EveryInc |
| **Size** | ~12 focused skills | 24 agents, 13 commands, 11 skills |
| **Philosophy** | Structured planning | "Each unit of work makes next easier" |

## Workflow Loops

### Superpowers

```
brainstorm → write-plan → execute-plan
     ↓            ↓             ↓
  clarify     detailed      run work
   idea        tasks       task-by-task
```

**Skills:**
- `superpowers:brainstorming` - Explore ideas, clarify requirements
- `superpowers:writing-plans` - Create bite-sized implementation plans
- `superpowers:executing-plans` - Execute in separate session with checkpoints
- `superpowers:subagent-driven-development` - Execute with fresh subagent per task

### Compound Engineering

```
plan → work → review → compound → repeat
  ↓      ↓       ↓         ↓
ideas  execute  verify   capture
                        learnings
```

**Commands:**
- `/workflows:plan` - Turn feature ideas into detailed plans
- `/workflows:work` - Execute with worktrees and task tracking
- `/workflows:review` - Multi-agent code review
- `/workflows:compound` - Document learnings for future work

## Feature Comparison

| Feature | Superpowers | Compound |
|---------|-------------|----------|
| **Planning** | `brainstorming` + `writing-plans` | `/workflows:plan` |
| **Execution** | `executing-plans` or `subagent-driven` | `/workflows:work` |
| **Review** | `requesting-code-review` | `/workflows:review` (multi-agent) |
| **Learning capture** | — | `/workflows:compound` |
| **Git worktrees** | `using-git-worktrees` | Built into `/workflows:work` |
| **TDD** | `test-driven-development` | Embedded in workflow |
| **Debugging** | `systematic-debugging` | — |
| **Specialized agents** | General purpose | Rails, design, security reviewers |

## The "Compound" Difference

Compound engineering's unique value is the **compound step** — explicitly capturing learnings:

```bash
/workflows:compound
```

This prompts you to:
1. Document what you learned
2. Update CLAUDE.md with patterns
3. Create reusable knowledge for future work

**Philosophy:** Traditional development accumulates tech debt. Compound engineering inverts this — each cycle makes the next easier.

## When to Use Each

### Use Superpowers when:
- Starting a new feature with unclear requirements
- Need structured planning with bite-sized tasks
- Want TDD-driven implementation
- Debugging complex issues (`systematic-debugging`)

### Use Compound when:
- Full development lifecycle (plan → ship)
- Want multi-agent code review
- Building knowledge base over time
- Working with domain-specific concerns (Rails, design)

### Use Both Together

```
superpowers:brainstorming     → clarify what to build
/workflows:plan               → detailed implementation plan
superpowers:subagent-driven   → execute with fresh agents
/workflows:review             → multi-agent review
/workflows:compound           → capture learnings
```

## Installation

**Superpowers** - included in qute-code-kit bundles:
```bash
./setup-project.sh ~/project --bundle minimal
```

**Compound Engineering** - fetch as external plugin:
```bash
python scripts/fetch-external.py github:EveryInc/compound-engineering-plugin
python scripts/build-marketplace.py
```

## Resources

- [Compound engineering: how Every codes with agents](https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents)
- [The story behind compounding engineering](https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it)
