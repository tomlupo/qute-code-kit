# Workflow Guide

Quick reference for day-to-day work with Claude Code and qute-code-kit. Keep this open while working.

## Work Modes

| Mode | Alias | Behavior |
|------|-------|----------|
| Development | `claude-dev` | Code first, explain after. Favor working solutions, run tests, atomic commits. |
| Research | `claude-research` | Read widely before concluding. Document findings. Don't code until understanding is clear. |
| Review | `claude-review` | Read thoroughly. Prioritize by severity. Suggest fixes, check security. |

Switch modes by launching Claude with the appropriate alias:

```bash
claude-dev        # Active development — implementation focus
claude-research   # Exploration — understanding before acting
claude-review     # Code review — quality and security focus
```

These inject mode-specific system prompts from `~/.claude/contexts/`. System prompt content has higher authority than user messages or tool results, so behavioral rules injected this way are reliably followed.

Setup (add to `~/.bashrc` or `~/.zshrc`):

```bash
alias claude-dev='claude --system-prompt "$(cat ~/.claude/contexts/dev.md)"'
alias claude-research='claude --system-prompt "$(cat ~/.claude/contexts/research.md)"'
alias claude-review='claude --system-prompt "$(cat ~/.claude/contexts/review.md)"'
```

---

## Workflows

### Feature Development

1. `claude-dev` mode
2. `/brainstorming` — explore the idea before coding
3. `/writing-plans` — design implementation approach
4. `/worktrees [branch]` — isolate work in a git worktree
5. `/executing-plans` — implement with review checkpoints
   > **Tip:** Prefix plans with: _"Steps are not complete until (a) related docs are updated, (b) stale/duplicate files are flagged, and (c) you summarize changes."_
6. `/requesting-code-review` — validate the work
7. `/commit` — atomic commit with generated message

### Debugging

1. `/systematic-debugging` — structured root cause analysis
2. Diagnose → hypothesize → verify → fix
3. `/verification-before-completion` — confirm the fix actually works

### Code Review (Giving)

1. `claude-review` mode
2. `/requesting-code-review` — multi-agent review
3. Checklist: logic, edge cases, security, performance, tests

### Code Review (Receiving)

1. `/receiving-code-review` — verify feedback before implementing
2. Technical rigor over performative compliance — push back on incorrect suggestions

### Research / Paper Reading

1. `claude-research` mode
2. `/paper-reading [path]` — three-pass reading approach
3. Summaries saved to `docs/papers/summaries/`

### External Second Opinions

1. `/llm-external-review` — gathers context, delegates to Codex or Gemini CLI
2. Codex for bugs and code review, Gemini for architecture and design

### Documentation

1. `/readme` — comprehensive README generation (runs as forked context)
2. `/doc-coauthoring` — structured co-writing workflow

### Data Fetching (Quant)

1. `/market-data-fetcher [ticker] [start] [end]`
2. Auto-routes to best source (Stooq, Yahoo, NBP, FRED, CCXT)

### Health Check (Personal)

1. `/garmin-health [command] [metric]`
2. Commands: `summary`, `trends hrv 7`, `compare`

### Long-Running Tasks (Headless)

1. `claude -p "instruction" --allowedTools "Bash,Read,Write,Edit"` — fire-and-forget
2. Useful for pipeline runs, batch doc updates, refactoring sweeps
3. Output: `--output-format json > result.json` or stream with `--output-format stream-json`

---

## Marketplace Plugins

### Automatic (Hook-Based)

These run in the background via hooks — no invocation needed.

| Plugin | What it does |
|--------|-------------|
| forced-eval | Reminds to check skills before jumping to implementation |
| strategic-compact | Suggests `/compact` at 50 tool calls, then every 25 |
| doc-enforcer | Reminds when 3+ code files edited without doc updates |
| skill-use-logger | Logs skill invocations to `.claude/skill-use-log.jsonl` |

### Session Management

- Auto-saves state on session exit (session-persistence)
- `/session-persistence:list` — see recent sessions
- `/session-persistence:load` — resume previous session state

### Notifications

- `/notifications:*` — push notifications via ntfy.sh when tasks complete

### Research Workflow (Marketplace)

- `/research-workflow:hypothesis` — document hypothesis
- `/research-workflow:experiment` — design experiment
- `/research-workflow:findings` — record findings

### Flow (Workflow Orchestration)

Lightweight lifecycle management with Manus-style discipline hooks. Works standalone or alongside compound-engineering.

```
Lifecycle: idea → brainstorm → plan → activate → work (with hooks) → complete
```

| Command | Purpose |
|---------|---------|
| `/flow:idea` | Capture idea to `docs/ideas/`, add to TASKS.md Later |
| `/flow:activate <path>` | Set active plan — hooks come alive |
| `/flow:deactivate` | Clear active plan — hooks go silent |
| `/flow:status` | Overview: active plan, tasks, ideas, completed |
| `/flow:complete` | Archive plan to `docs/plans/completed/`, update TASKS.md |
| `/flow:handoff` | Flow-aware session handoff document |

**With compound-engineering**: `/workflows:plan` creates the plan, `/flow:activate` tracks it, `/flow:complete` archives it.

**Standalone**: Create plans manually or via `/brainstorming` + `/writing-plans`, then activate and track.

### External Plugins (Optional)

Install via their respective setup scripts.

- **adaptive-learning** — observes tool usage, learns instincts, surfaces them at session start
  - `/adaptive-learning:status`, `/adaptive-learning:analyze`, `/adaptive-learning:export`
- **compound-engineering** — full dev lifecycle
  - `/workflows:brainstorm` → `/workflows:plan` → `/workflows:work` → `/workflows:review`

---

## Skill Quick Reference

### Always Available (Minimal Bundle)

| Skill | Trigger | Example |
|-------|---------|---------|
| `/commit` | "commit this" | `/commit` |
| `/worktrees` | "work in isolation" | `/worktrees feature-auth` |
| `/readme` | "write readme" | `/readme` |
| `/llm-external-review` | "ask codex", "second opinion" | `/llm-external-review` |
| `/generating-commit-messages` | (auto on commit) | automatic |

### Quant Bundle

| Skill | Trigger | Example |
|-------|---------|---------|
| `/paper-reading` | "read this paper" | `/paper-reading docs/paper.pdf` |
| `/market-data-fetcher` | "get stock prices" | `/market-data-fetcher AAPL 2024-01-01` |
| `/sql-patterns` | "write a query" | `/sql-patterns` |
| `/qrd` | "research spec" | `/qrd` |
| `/garmin-health` | "health stats" | `/garmin-health summary` |
| `/context-management` | (auto on long sessions) | automatic |
| `/gist-report` | "share as HTML" | `/gist-report` |
| `/gist-transcript` | "save session" | `/gist-transcript` |

### Webdev Bundle

| Skill | Trigger | Example |
|-------|---------|---------|
| `/pdf-skill` | "extract from PDF" | `/pdf-skill` |
| `/context-management` | (auto) | automatic |
| `/gist-report` | "share as HTML" | `/gist-report` |

### Superpowers (Always Available via Marketplace)

| Skill | When to use |
|-------|-------------|
| `/brainstorming` | Before any creative work |
| `/systematic-debugging` | On any bug or failure |
| `/writing-plans` | Before multi-step implementation |
| `/executing-plans` | To implement a written plan |
| `/requesting-code-review` | After completing work |
| `/receiving-code-review` | When given review feedback |
| `/verification-before-completion` | Before claiming done |
| `/test-driven-development` | Before writing implementation |
| `/finishing-a-development-branch` | When ready to merge |

---

## Context Management

- **strategic-compact** plugin auto-reminds at 50 tool calls
- `/compact` manually when context feels heavy
- Save big outputs to files, show summaries in chat
- Use `Task(Explore)` for codebase questions — protects main context
- For architecture questions, spawn 2-3 parallel Explore agents with different search focuses
- Paper reading: save summaries to files, not in conversation

## System Prompt Injection

Rules in `.claude/rules/` auto-load every session. Skills load on demand.

For strict behavioral rules, inject via CLI flag:

```bash
claude --system-prompt "$(cat contexts/dev.md)"
```

Instruction hierarchy: **system prompt > user message > tool output**.

Aliases (`claude-dev`, `claude-research`, `claude-review`) make this ergonomic — see [Work Modes](#work-modes).

## Kit Management

```bash
# Add a single component
./setup-project.sh ~/project --add my:skill-name

# Add a sub-bundle
./setup-project.sh ~/project --add @skills/visualization

# Preview changes (dry run)
./setup-project.sh ~/project --bundle quant --diff

# Update project to latest kit
./setup-project.sh ~/project --bundle quant --update

# Check what's installed
cat ~/project/.claude/.toolkit-manifest.json
```

## Available Sub-Bundles (Add on Demand)

| Sub-bundle | Skills included | Add with |
|------------|----------------|----------|
| `@skills/ml-core` | scikit-learn, shap, pytorch-lightning, aeon, EDA | `--add @skills/ml-core` |
| `@skills/statistics` | statsmodels, pymc, scikit-survival, statistical-analysis | `--add @skills/statistics` |
| `@skills/visualization` | matplotlib, seaborn, plotly, networkx, sci-viz, umap | `--add @skills/visualization` |
| `@skills/data-processing` | polars, dask, vaex | `--add @skills/data-processing` |
| `@skills/research-tools` | openalex, perplexity, literature-review, citations | `--add @skills/research-tools` |
