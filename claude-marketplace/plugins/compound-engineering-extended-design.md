# Compound Engineering Extended - Design Document

> Fork of [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) with enhanced context preservation, TASKS.md integration, and RALPH loop methodology.

## Philosophy

### Original Compound Philosophy
> "Each unit of engineering work should make subsequent units easier—not harder."

### Extended Philosophy
> "Each session builds on the last. Nothing is lost. Knowledge compounds across time."

### Core Principles
- **80/20 Rule**: 80% planning and review, 20% execution
- **Intelligent Flow**: Each step proposes the logical next step
- **Memory Persistence**: Context survives across sessions
- **Iterative Research**: RALPH loop for hypothesis-driven work

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY LAYERS                                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  LONG-TERM MEMORY: docs/solutions/                      │    │
│  │  "What we learned" - persists forever                   │    │
│  │  Fed by: /workflows:compound                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ▲                                     │
│                            │                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  WORKING MEMORY: TASKS.md + docs/plans/                 │    │
│  │  "What we're doing" - active projects                   │    │
│  │  Fed by: /workflows:plan, task completion               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ▲                                     │
│                            │                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SESSION MEMORY: .claude/handoffs/                      │    │
│  │  "Where we left off" - context preservation             │    │
│  │  Fed by: /handoff, PreCompact hook                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## What We Keep from Compound Engineering

### Workflow Cycle (Core)
| Command | Purpose |
|---------|---------|
| `/workflows:brainstorm` | Explore WHAT to build through dialogue |
| `/workflows:plan` | Transform ideas into detailed plans |
| `/workflows:work` | Execute plans with quality |
| `/workflows:review` | Multi-agent code review |
| `/workflows:compound` | Document learnings for reuse |

### Agents (28 existing)
- `kieran-rails-reviewer` - Rails conventions
- `security-sentinel` - Security analysis
- `performance-oracle` - Performance review
- `architecture-strategist` - Architecture decisions
- `code-simplicity-reviewer` - Simplification
- `best-practices-researcher` - External research
- `framework-docs-researcher` - Documentation lookup
- `repo-research-analyst` - Local codebase analysis
- `learnings-researcher` - Search docs/solutions/
- ... and 19 more specialized agents

### Skills (15 existing)
- `brainstorming` - Idea exploration techniques
- `compound-docs` - Solution documentation
- `file-todos` - Todo file management
- `git-worktree` - Parallel development
- `frontend-design` - UI implementation
- ... and 10 more

### Quality Patterns
- AskUserQuestion for "what's next" flow
- Parallel Task() execution for agents
- Structured command frontmatter
- `<thinking>` blocks for reasoning
- docs/ organization (plans, brainstorms, solutions)

---

## What We Add

### New Commands

#### `/handoff` - Save Session State
```markdown
---
name: handoff
description: Save session state for seamless continuation later
argument-hint: "[--clear]"
---
```

**Purpose:** Manual state save before /clear or session end.

**Behavior:**
1. Capture current goal, progress, decisions, files
2. Write to `.claude/handoffs/YYYY-MM-DD-HHMM.md`
3. Update TASKS.md with `@handoff:` annotation
4. Suggest /clear or continue

**Output:**
```
✅ Handoff saved: .claude/handoffs/2026-01-23-1430.md
✅ TASKS.md updated: added @handoff annotation

Ready to clear context. Options:
1. /clear now
2. Continue working
```

---

#### `/resume` - Continue from Handoff
```markdown
---
name: resume
description: Continue work from last handoff
argument-hint: "[handoff-file]"
---
```

**Purpose:** Load context and continue after /clear or new session.

**Behavior:**
1. Find handoff (from TASKS.md @handoff or latest file)
2. Load handoff + linked plan
3. Display state summary
4. Offer continuation options

**Output:**
```
Resuming: Signal Backtest

From: 2026-01-23 14:30 (2h ago)
Phase: work
Iteration: 2/3

Progress:
- [x] Data loader
- [x] Signal calc
- [ ] Backtest engine ← YOU ARE HERE
- [ ] Metrics

What's next?
1. Continue work → /workflows:work [plan] (Recommended)
2. Check iteration → /iterate check
3. Review progress → /workflows:review
4. See full handoff
5. Start fresh
```

---

#### `/tasks` - Interact with TASKS.md
```markdown
---
name: tasks
description: View and manage TASKS.md
argument-hint: "[list|add|complete|park] [task-name]"
---
```

**Subcommands:**
- `/tasks` or `/tasks list` - Show current tasks with status
- `/tasks add "task name"` - Add new task to Now section
- `/tasks complete [task]` - Move to Completed, prompt for @solution
- `/tasks park [task]` - Move to Parked with reason

---

#### `/iterate` - RALPH Loop Management
```markdown
---
name: iterate
description: Manage RALPH loop iterations
argument-hint: "[init|check|next|close] [task-name]"
---
```

**Subcommands:**

**`/iterate init [task]`** - Initialize iteration tracking
- Verify plan has acceptance criteria
- Set `@iteration:1` in TASKS.md
- Display iteration tracker

**`/iterate check [task]`** - Check criteria status
- Run criteria-validator agent
- Show pass/fail status
- Offer iterate/close options

**`/iterate next [task]`** - Advance iteration
- Increment `@iteration:N`
- Check against max
- Log in plan file

**`/iterate close [task] [success|rejected]`** - Close loop
- Success: proceed to review
- Rejected: document learning, move to Parked

---

### New Agents

#### `handoff-curator`
```markdown
---
name: handoff-curator
description: Creates rich, resumable handoffs capturing full session context
model: haiku
tools: [Read, Write, Grep, Glob]
---
```

**Extracts:**
- Current goal and progress
- Key decisions with rationale
- Active files and their state
- Blockers and unknowns
- Exact resume command

---

#### `task-orchestrator`
```markdown
---
name: task-orchestrator
description: Manages TASKS.md state, tracks iterations, links artifacts
model: haiku
tools: [Read, Write, Edit]
---
```

**Handles:**
- Task creation from plans
- Annotation management (@plan, @handoff, @solution, @iteration)
- Status transitions (Now → Completed → Parked)
- Iteration counting for RALPH loops

---

#### `context-sentinel`
```markdown
---
name: context-sentinel
description: Monitors context usage, warns before overflow, suggests saves
model: haiku
tools: [Read]
---
```

**Proactive monitoring:**
- Estimates context usage
- Warns at 70%, 85% thresholds
- Suggests /handoff before critical
- Recommends what to offload to files

---

#### `criteria-validator`
```markdown
---
name: criteria-validator
description: Validates work against plan's acceptance criteria
model: sonnet
tools: [Read, Bash, Grep]
---
```

**For RALPH loop:**
- Extracts criteria from plan
- Runs verification commands
- Checks metrics against thresholds
- Returns pass/fail with evidence

---

#### `memory-linker`
```markdown
---
name: memory-linker
description: Connects related solutions, plans, and tasks across knowledge base
model: haiku
tools: [Read, Grep, Glob, Edit]
---
```

**Maintains knowledge graph:**
- Links related solutions
- Suggests relevant past work during planning
- Updates cross-references

---

### New Skills

#### `session-continuity/`
```
skills/session-continuity/
├── SKILL.md
├── references/
│   ├── handoff-patterns.md      # Best practices for handoffs
│   ├── resume-strategies.md     # How to resume effectively
│   └── context-budgeting.md     # Managing token limits
└── assets/
    └── handoff-template.md      # Standard handoff format
```

---

#### `task-management/`
```
skills/task-management/
├── SKILL.md
├── references/
│   ├── tasks-md-format.md       # TASKS.md structure
│   ├── annotations.md           # @plan, @handoff, @solution, @iteration
│   └── workflows.md             # Task lifecycle
└── assets/
    └── tasks-template.md        # TASKS.md template
```

---

#### `ralph-methodology/`
```
skills/ralph-methodology/
├── SKILL.md
├── references/
│   ├── iteration-patterns.md    # How to iterate effectively
│   ├── acceptance-criteria.md   # Writing good criteria
│   ├── hypothesis-testing.md    # Scientific method
│   └── failure-documentation.md # Learning from failures
└── assets/
    ├── ralph-plan-template.md   # Plan with criteria section
    └── iteration-tracker.md     # Tracking format
```

---

### Hooks

#### `hooks.json`
```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/auto_handoff.py",
            "timeout": 10000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_active_work.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": {"tools": ["Write", "Edit"]},
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/track_changes.py"
          }
        ]
      }
    ]
  }
}
```

**Hook Purposes:**
- **PreCompact**: Auto-generate handoff when context fills
- **Stop**: Remind to /handoff if work in progress
- **PostToolUse**: Track file changes for handoff context

---

## Modified Existing Commands

### `/workflows:plan` Modifications

**Add Acceptance Criteria Section:**
```markdown
## Acceptance Criteria

### Must Pass (gates iteration)
- [ ] Criterion 1 with measurable target
- [ ] Criterion 2 with verification method

### Verification Commands
| Criterion | Command |
|-----------|---------|
| Tests pass | `pytest tests/` |
| Metric X > Y | `python evaluate.py --metric X` |

### Iteration Limits
- **Max iterations:** 3
- **Reassess trigger:** 2 failures on same criterion
```

**Add TASKS.md Integration:**
- After writing plan, create/link task in TASKS.md
- Add `@plan:` annotation

**Enhanced Post-Generation Options:**
```
What's next?
1. Start work → /workflows:work (Recommended)
2. Review plan → /workflows:review
3. Set up RALPH loop → /iterate init
4. Deepen plan → /deepen-plan
5. Other
```

---

### `/workflows:work` Modifications

**Add Task Binding:**
- At start: find and bind to TASKS.md task
- During: track progress in plan file (check off items)
- On handoff: update @handoff annotation

**Enhanced Completion Options:**
```
✅ Work complete!

Plan: docs/plans/2026-01-23-signal-plan.md
Progress: 5/5 tasks done

What's next?
1. Review code → /workflows:review (Recommended)
2. Mark task complete → update TASKS.md
3. Document learnings → /workflows:compound
4. Continue working
```

---

### `/workflows:compound` Modifications

**Add TASKS.md Integration:**
- After creating solution, link to completed task
- Add `@solution:` annotation
- Offer to mark task complete

**Enhanced Post-Compound Options:**
```
✅ Solution documented!

Created: docs/solutions/backtesting/signal-validation.md

What's next?
1. Mark task complete → update TASKS.md (Recommended)
2. Create PR
3. Start next task → show TASKS.md Next section
4. Done for now
```

---

## Flow Diagrams

### Complete Workflow Cycle

```
/workflows:brainstorm
        │
        ▼
    docs/brainstorms/YYYY-MM-DD-topic.md
        │
        ▼
/workflows:plan
        │
        ├──► docs/plans/YYYY-MM-DD-plan.md
        │
        └──► TASKS.md
             - [ ] Task `@plan:...`
        │
        ▼
/workflows:work
        │
        ├──► Plan items checked off
        │
        └──► TASKS.md unchanged (in progress)
        │
        ▼
/workflows:review
        │
        ├──► Code quality verified
        │
        └──► Issues fixed if any
        │
        ▼
/workflows:compound
        │
        ├──► docs/solutions/category/solution.md
        │
        └──► TASKS.md
             - [x] Task `@solution:...` (Completed)
```

---

### Handoff/Resume Flow

```
SESSION 1                           SESSION 2
─────────                           ─────────

/workflows:work                     /resume
        │                                │
   [working...]                     Load handoff
        │                           Show context
   [context filling]                     │
        │                           "Continue?"
        ▼                                │
/handoff                                 ▼
        │                           /workflows:work
        ▼                           (continues from where left off)
TASKS.md updated
   @handoff:...
        │
        ▼
/clear
        │
        ▼
[session ends]
```

---

### RALPH Loop Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      RALPH LOOP                                  │
│                                                                  │
│  HYPOTHESIZE ──► /workflows:brainstorm                          │
│       │                                                          │
│       ▼                                                          │
│    PLAN ──────► /workflows:plan (with acceptance criteria)      │
│       │                                                          │
│       ▼                                                          │
│  ┌────────────────────────────────────────┐                     │
│  │         ITERATION LOOP                 │                     │
│  │                                        │                     │
│  │   ACT ────► /workflows:work            │                     │
│  │    │                                   │                     │
│  │    ▼                                   │                     │
│  │  ASSESS ──► /iterate check             │                     │
│  │    │                                   │                     │
│  │    ├── PASS ──► exit loop              │                     │
│  │    │                                   │                     │
│  │    └── FAIL                            │                     │
│  │         │                              │                     │
│  │         ├── iteration < max            │                     │
│  │         │    └──► /iterate next        │                     │
│  │         │         └──► refine, retry   │                     │
│  │         │                              │                     │
│  │         └── iteration >= max           │                     │
│  │              └──► reject hypothesis    │                     │
│  │                                        │                     │
│  └────────────────────────────────────────┘                     │
│       │                                                          │
│       ▼                                                          │
│   LEARN ─────► /workflows:review                                │
│       │        /workflows:compound                              │
│       ▼                                                          │
│  REFLECT ────► Mark complete or document failure                │
│       │                                                          │
│       └──────► Next hypothesis                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### "What's Next" Chain

```
/workflows:work completes
         │
         ▼
┌─────────────────────────────────────────────────┐
│ What's next?                                     │
│ 1. Review code → /workflows:review (Recommended)│
│ 2. Mark task complete                            │
│ 3. Document learnings → /workflows:compound     │
└───────────────────────┬─────────────────────────┘
                        │ User picks 1
                        ▼
/workflows:review completes
         │
         ▼
┌─────────────────────────────────────────────────┐
│ What's next?                                     │
│ 1. Document learnings → /workflows:compound (R) │
│ 2. Fix findings → /resolve_todo_parallel        │
│ 3. Mark task complete                            │
└───────────────────────┬─────────────────────────┘
                        │ User picks 1
                        ▼
/workflows:compound completes
         │
         ▼
┌─────────────────────────────────────────────────┐
│ What's next?                                     │
│ 1. Mark task complete (Recommended)             │
│ 2. Create PR                                     │
│ 3. Start next task                               │
└───────────────────────┬─────────────────────────┘
                        │ User picks 1
                        ▼
Task marked complete
         │
         ▼
┌─────────────────────────────────────────────────┐
│ What's next?                                     │
│ 1. Create PR → /commit-push-pr                  │
│ 2. Start next task → /workflows:plan            │
│ 3. Done for now                                  │
└─────────────────────────────────────────────────┘
```

---

## TASKS.md Format

```markdown
# TASKS.md

## Now
- [ ] Signal backtest `@plan:docs/plans/2026-01-23-signal.md` `@iteration:2` `@handoff:2026-01-23-1430.md`
- [ ] Data pipeline fix `@plan:docs/plans/2026-01-22-pipeline.md`

## Next
- [ ] Multi-factor model
- [ ] Risk parity allocation
- [ ] Portfolio optimization

## Completed
- [x] Feature engineering `@solution:docs/solutions/data-pipelines/feature-scaling.md`
- [x] Data loader `@solution:docs/solutions/infrastructure/async-loader.md`

## Parked
- [ ] ~Momentum signal~ `@iterations:3` `@outcome:rejected`
      Reason: Could not achieve Sharpe > 1.0 after 3 iterations

---

## Annotations Reference

| Annotation | Meaning |
|------------|---------|
| `@plan:path` | Links to planning document |
| `@handoff:file` | Work in progress, has saved state |
| `@solution:path` | Completed, knowledge captured |
| `@iteration:N` | Current iteration in RALPH loop |
| `@iterations:N` | Total iterations attempted (for parked) |
| `@outcome:success\|rejected` | Final outcome (for parked) |
```

---

## Handoff Template

```markdown
# Handoff: [Current Goal]

Generated: YYYY-MM-DD HH:MM
Context: ~X% used

## Active Work

- **Task:** [from TASKS.md]
- **Plan:** [linked plan path]
- **Phase:** brainstorm | plan | work | review | compound
- **Iteration:** N/M (if RALPH loop)

## Progress

### Completed
- [x] Item from plan
- [x] Another item

### Remaining
- [ ] Next item ← RESUME HERE
- [ ] Final item

## Session Context

### Key Decisions
- Decision 1: chose X because Y
- Decision 2: using approach Z

### Modified Files
- path/to/file.py (description of changes)
- path/to/test.py (added tests for X)

### Blockers / Unknowns
- Need clarification on X
- Waiting for Y

## Resume

```bash
/resume

# Or directly:
/workflows:work docs/plans/YYYY-MM-DD-plan.md
```
```

---

## Directory Structure

```
compound-engineering-extended/
├── .claude-plugin/
│   └── plugin.json
├── CHANGELOG.md
├── CLAUDE.md
├── LICENSE
├── README.md
│
├── agents/
│   ├── (existing 28 agents...)
│   ├── handoff-curator.md         # NEW
│   ├── task-orchestrator.md       # NEW
│   ├── context-sentinel.md        # NEW
│   ├── criteria-validator.md      # NEW
│   └── memory-linker.md           # NEW
│
├── commands/
│   ├── workflows/
│   │   ├── brainstorm.md          # existing
│   │   ├── plan.md                # MODIFIED
│   │   ├── work.md                # MODIFIED
│   │   ├── review.md              # existing
│   │   └── compound.md            # MODIFIED
│   ├── handoff.md                 # NEW
│   ├── resume.md                  # NEW
│   ├── tasks.md                   # NEW
│   ├── iterate.md                 # NEW
│   └── (other existing commands...)
│
├── skills/
│   ├── (existing 15 skills...)
│   ├── session-continuity/        # NEW
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── handoff-patterns.md
│   │   │   ├── resume-strategies.md
│   │   │   └── context-budgeting.md
│   │   └── assets/
│   │       └── handoff-template.md
│   ├── task-management/           # NEW
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── tasks-md-format.md
│   │   │   ├── annotations.md
│   │   │   └── workflows.md
│   │   └── assets/
│   │       └── tasks-template.md
│   └── ralph-methodology/         # NEW
│       ├── SKILL.md
│       ├── references/
│       │   ├── iteration-patterns.md
│       │   ├── acceptance-criteria.md
│       │   ├── hypothesis-testing.md
│       │   └── failure-documentation.md
│       └── assets/
│           ├── ralph-plan-template.md
│           └── iteration-tracker.md
│
├── hooks/
│   └── hooks.json                 # NEW
│
├── scripts/
│   ├── auto_handoff.py            # NEW
│   ├── check_active_work.py       # NEW
│   └── track_changes.py           # NEW
│
└── templates/
    ├── handoff-template.md        # NEW
    ├── tasks-template.md          # NEW
    └── ralph-plan-template.md     # NEW
```

---

## Quality Standards

### Command Pattern
```markdown
---
name: command-name
description: Clear one-line description
argument-hint: "[what args look like]"
---

# Command Title

## Introduction
<role>Expert persona</role>

## Input
<input_document> #$ARGUMENTS </input_document>

## Main Tasks
<task_list>
- [ ] Step with clear outcome
</task_list>

### Phase N: Name
<thinking>
Reasoning about approach
</thinking>

<parallel_tasks>
- Task agent-one(context)
- Task agent-two(context)
</parallel_tasks>

## Post-Action Options
Use **AskUserQuestion** tool:
1. Recommended next → command
2. Alternative → command
3. Other
```

### Agent Pattern
```markdown
---
name: agent-name
description: What it does, when to use
model: sonnet|opus|haiku
tools: [list of tools]
---

# Agent Name

<role>Expert persona</role>

## Purpose
Clear mission statement

## Inputs
What it receives

## Process
1. Step one
2. Step two

## Outputs
What it returns

## Integration
How it fits with other agents
```

### Skill Pattern
```
skills/skill-name/
├── SKILL.md          # Entry point with overview
├── references/       # Detailed documentation
└── assets/           # Templates and configs
```

### Quality Checklist
- [ ] Follows frontmatter pattern exactly
- [ ] Uses `<thinking>` blocks for reasoning
- [ ] Uses `<parallel_tasks>` for concurrent agents
- [ ] Ends with AskUserQuestion offering next steps
- [ ] Includes clear examples
- [ ] Documents preconditions
- [ ] Specifies which agents/skills it calls
- [ ] Integrates with existing workflow commands
- [ ] Supports memory architecture

---

## Implementation Priority

### Phase 1: Core Context Preservation
1. `/handoff` command
2. `/resume` command
3. `hooks.json` with PreCompact
4. `handoff-curator` agent
5. `session-continuity` skill

### Phase 2: TASKS.md Integration
1. `/tasks` command
2. Modify `/workflows:plan` for task creation
3. Modify `/workflows:work` for task binding
4. Modify `/workflows:compound` for solution linking
5. `task-orchestrator` agent
6. `task-management` skill

### Phase 3: RALPH Loop
1. `/iterate` command
2. `criteria-validator` agent
3. `ralph-methodology` skill
4. Enhanced plan template with acceptance criteria

### Phase 4: Polish
1. `context-sentinel` agent
2. `memory-linker` agent
3. Documentation and examples
4. Testing across workflows

---

## Summary

| Category | Existing | New | Total |
|----------|----------|-----|-------|
| Commands | 24 | 4 | 28 |
| Agents | 28 | 5 | 33 |
| Skills | 15 | 3 | 18 |
| Hooks | 0 | 3 | 3 |

**Key Additions:**
- Memory architecture (long-term, working, session)
- TASKS.md as persistent task tracker
- Handoff/resume for context preservation
- RALPH loop for iterative research
- Intelligent "what's next" flow throughout

**Philosophy Preserved:**
- Each unit of work makes subsequent work easier
- 80% planning/review, 20% execution
- Knowledge compounds over time
