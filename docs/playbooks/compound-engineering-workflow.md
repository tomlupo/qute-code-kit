# Compound Engineering Workflow

> Full development lifecycle where each unit of work makes the next easier.

## The Idea

Compound engineering is recursive self-improvement for your codebase. Every problem you solve gets captured as a learning (`docs/solutions/`), which future planning agents read before writing new plans. Over time, the system gets smarter about *your* project — avoiding past mistakes, reusing proven patterns, and building on what worked.

## When to Use

Full plan-to-ship lifecycle, want multi-agent code review, or building a knowledge base of solutions over time.

## Flow

```
brainstorm → plan → deepen → work → review → triage → resolve → compound
                                                                    |
                                docs/solutions/ ←───────────────────┘
                                     |
                                next plan reads past learnings
```

## Steps

### 1. Brainstorm (optional)

```
/workflows:brainstorm
```

Asks one question at a time, explores 2-3 approaches. Spawns `repo-research-analyst` for existing patterns. Output: `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`. Skip if requirements are already clear.

### 2. Plan

```
/workflows:plan
```

Auto-reads recent brainstorm. Spawns research agents (`repo-research-analyst`, `learnings-researcher`, optionally `best-practices-researcher`, `framework-docs-researcher`). Detail levels: MINIMAL / MORE / A LOT. Output: `docs/plans/YYYY-MM-DD-feat-<name>-plan.md`.

### 3. Deepen Plan (optional)

```
/deepen-plan
```

Enhances plan with massive parallel research — 30-50+ agents: matched skills, `docs/solutions/` entries, Context7 queries, web searches. Output: enhanced plan with "Research Insights" subsections.

### 4. Work

```
/workflows:work
```

Creates branch/worktree, TodoWrite task list, implements step by step. Incremental commits at logical units, continuous tests. Output: PR with commits.

### 5. Review

```
/workflows:review
```

13+ specialist agents in parallel:

| Agent | Focus |
|-------|-------|
| `security-sentinel` | OWASP Top 10, auth, injection |
| `performance-oracle` | N+1 queries, memory, caching |
| `architecture-strategist` | Component boundaries, coupling |
| `code-simplicity-reviewer` | YAGNI, minimalism |
| `data-integrity-guardian` | Migrations, privacy |
| `pattern-recognition-specialist` | Patterns & anti-patterns |
| `kieran-python-reviewer` | Strict Python conventions |
| `kieran-typescript-reviewer` | Strict TS conventions |

Output: `todos/*-pending-{p1|p2|p3}-*.md` — P1 findings block merge.

### 6. Triage

```
/triage
```

Presents each finding one by one (runs on Haiku for speed). User says: **yes** (approve) / **next** (skip) / **custom** (modify). Output: approved items become `todos/*-ready-*.md`.

### 7. Resolve

```
/resolve_todo_parallel
```

Spawns `pr-comment-resolver` per todo in parallel. Commits fixes, marks todos complete. Also: `/resolve_parallel` (TODO comments in code), `/resolve_pr_parallel` (PR review comments).

### 8. Compound

```
/workflows:compound
```

Capture what was learned. Spawns 6 parallel subagents. Output: `docs/solutions/<category>/<symptom>-<module>-YYYYMMDD.md`. Categories: performance, database, security, UI, integration, logic, build, test, runtime.

## Shortcuts

| Command | What it does |
|---------|-------------|
| `/lfg` | Full autonomous loop: plan → deepen → work → review → resolve → test |
| `/slfg` | Same with swarm mode (parallel specialist subagents) |
| `/plan_review` | Quick 3-agent plan review |

## File Artifacts

```
docs/brainstorms/    ← /workflows:brainstorm
docs/plans/          ← /workflows:plan (PROTECTED — never deleted)
docs/solutions/      ← /workflows:compound (PROTECTED — knowledge base)
todos/               ← /workflows:review + /triage + /resolve
```

## Combining with Superpowers

```
superpowers:brainstorming     → clarify what to build
/workflows:plan               → detailed plan with research
/deepen-plan                  → enhance with research agents
superpowers:subagent-driven   → execute with fresh agents
/workflows:review             → multi-agent review
/workflows:compound           → capture learnings
```

See `superpowers-workflow.md` for the superpowers side.

## Practitioner Tips

- **Brainstorm first when uncertain** — the one-question-at-a-time format forces you to clarify requirements before wasting tokens on planning
- **Plan detail level matters** — use MINIMAL for familiar territory, A LOT for unfamiliar domains or complex integrations
- **Deepen selectively** — `/deepen-plan` spawns 30-50+ agents; use it for critical features, skip for routine work
- **Worktrees for isolation** — `/workflows:work` creates a worktree so your main branch stays clean during implementation
- **Triage ruthlessly** — most P2/P3 review findings are noise. Focus on P1s, say "next" to everything else
- **Compound after every significant fix** — don't wait for a full feature. A tricky bug fix is worth compounding immediately
- **The loop compounds** — `docs/solutions/` is the flywheel. The more you capture, the better future plans become. This is the core insight: each cycle makes the next cycle better

## References

- [Practitioner's Guide to Compound Engineering](https://every.to/p/a-practitioner-s-guide-to-compound-engineering) — Every article with in-depth walkthrough
- [Video walkthrough](https://youtu.be/IQ1_5jPiQoE) — YouTube tutorial on the plugin
