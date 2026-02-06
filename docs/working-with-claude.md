# Working Effectively with Claude

Comprehensive reference for using qute-code-kit tools, plugins, skills, and agents in AI-assisted development.

## Session Lifecycle

Every Claude session has an automated lifecycle powered by plugins that fire on specific events.

### Hook Event Map

| Event | Plugin | What it does |
|-------|--------|-------------|
| `SessionStart` | adaptive-learning | Loads top 5 instincts (confidence >= 0.3) from `~/.claude/adaptive-learning/instincts/` |
| `SessionStart` | session-persistence | Scans `~/.claude/sessions/` for `.tmp` files from last 7 days, surfaces top 3 unfinished sessions |
| `UserPromptSubmit` | forced-eval | Injects mandatory 3-step evaluation: EVALUATE skills/MCP/agents -> ACTIVATE -> IMPLEMENT |
| `PreToolUse` | strategic-compact | Increments per-session tool call counter. At threshold (default 50), suggests `/compact`. Repeats every 25 after. |
| `PostToolUse` | adaptive-learning | Logs tool name, truncated I/O, session context to `observations.jsonl` (auto-rotates at 10MB) |
| `PostToolUse` | doc-enforcer | Tracks code vs doc file edits. After 3+ code files without a doc edit, surfaces reminder. |
| `PostToolUse` | skill-use-logger | Appends skill invocations to `.claude/skill-use-log.jsonl` |
| `PostToolUse` | ruff-formatter | Auto-formats `.py` files with `ruff format` + `ruff check --fix` after edits. Silently skips if ruff unavailable. |
| `PostToolUse` | notifications | On long-running Bash commands (>30s), sends push notification via ntfy.sh |
| `PreCompact` | strategic-compact | Logs compaction events to `.claude/compact-log.jsonl` |
| `Stop` | session-persistence | Writes structured session file to `~/.claude/sessions/{date}-{id}-session.tmp` |

All hooks use try/except with `sys.exit(0)` — they never block sessions. Session-scoped state is keyed by `CLAUDE_SESSION_ID` in `/tmp/`.

### Environment Variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `CLAUDE_SESSION_ID` | All session-scoped plugins | Unique session identifier |
| `CLAUDE_PLUGIN_ROOT` | All plugin scripts | Plugin root directory |
| `DOC_ENFORCER_THRESHOLD` | doc-enforcer | Code files before reminder (default 3) |
| `COMPACT_THRESHOLD` | strategic-compact | Tool calls before first suggestion (default 50) |
| `COMPACT_INTERVAL` | strategic-compact | Tool calls between repeated suggestions (default 25) |

## Work Modes

The toolkit supports different work modes via CLI aliases, each optimizing Claude's behavior for specific tasks:

| Mode | Alias | Behavior |
|------|-------|----------|
| Development | `claude-dev` | Code first, explain after. Working solutions, tests, atomic commits. |
| Research | `claude-research` | Read widely before concluding. Document findings. No code until clear. |
| Review | `claude-review` | Read thoroughly. Prioritize by severity. Check security. |

### Setting Up Work Modes

Create context files and shell aliases:

```bash
# Create context directory
mkdir -p ~/.claude/contexts

# Create mode-specific context files
cat > ~/.claude/contexts/dev.md << 'EOF'
# Development Mode
Prioritize working code over explanation. Write tests. Make atomic commits.
When in doubt, ship something working and iterate.
EOF

cat > ~/.claude/contexts/research.md << 'EOF'
# Research Mode
Read widely before concluding. Document sources and findings.
No code until requirements are crystal clear.
EOF

cat > ~/.claude/contexts/review.md << 'EOF'
# Review Mode
Read thoroughly before commenting. Prioritize issues by severity.
Check for security vulnerabilities. Be constructive.
EOF

# Add aliases to your shell config (~/.bashrc or ~/.zshrc)
alias claude-dev='claude --context ~/.claude/contexts/dev.md'
alias claude-research='claude --context ~/.claude/contexts/research.md'
alias claude-review='claude --context ~/.claude/contexts/review.md'
```

## Workflows

### Planning & Development Cycle

Two complementary planning systems — use either or combine them.

**Superpowers** (structured planning):

```
brainstorm → write-plan → execute-plan
     |            |             |
  clarify     detailed      run work
   idea        tasks       task-by-task
```

- `superpowers:brainstorming` — Explore ideas, clarify requirements
- `superpowers:writing-plans` — Create bite-sized implementation plans
- `superpowers:executing-plans` — Execute in separate session with checkpoints
- `superpowers:subagent-driven-development` — Execute with fresh subagent per task

**Compound Engineering** (knowledge-compounding lifecycle):

```
brainstorm → plan → deepen → work → review → triage → resolve → compound
                                                                    |
                                    docs/solutions/ ←───────────────┘
                                         |
                                    next plan reads past learnings
```

**Step 1: `/workflows:brainstorm`** — Clarify WHAT to build
- Asks one question at a time, explores 2-3 approaches, applies YAGNI
- Spawns: `repo-research-analyst` for existing patterns
- Output: `docs/brainstorms/YYYY-MM-DD-<topic>-brainstorm.md`
- Skip if: requirements are already clear

**Step 2: `/workflows:plan`** — Detail HOW to build it
- Auto-reads recent brainstorm from `docs/brainstorms/`
- Spawns: `repo-research-analyst`, `learnings-researcher` (searches `docs/solutions/`), optionally `best-practices-researcher`, `framework-docs-researcher`, `spec-flow-analyzer`
- Detail levels: MINIMAL / MORE / A LOT
- Output: `docs/plans/YYYY-MM-DD-feat-<name>-plan.md`

**Step 3: `/deepen-plan`** — Enhance with massive parallel research
- Discovers ALL skills, agents, and learnings dynamically (no hardcoding)
- Spawns 30-50+ parallel agents: every matched skill, every `docs/solutions/` entry, Context7 queries, web searches
- Output: enhanced plan with "Research Insights" subsections

**Step 4: `/workflows:work`** — Execute the plan
- Creates branch/worktree via `git-worktree` skill
- TodoWrite task list, implements step by step
- Incremental commits at logical units, continuous tests
- Optional: Figma sync (`figma-design-sync` agent), lint checks
- Output: PR with screenshots and commits

**Step 5: `/workflows:review`** — Multi-agent code review (13+ agents in parallel)
- Agents: `security-sentinel`, `performance-oracle`, `architecture-strategist`, `code-simplicity-reviewer`, `data-integrity-guardian`, `pattern-recognition-specialist`, `agent-native-reviewer`, `kieran-python-reviewer`, `kieran-typescript-reviewer`, `kieran-rails-reviewer`, `dhh-rails-reviewer`, `schema-drift-detector`, `design-implementation-reviewer`
- Conditional: `data-migration-expert` + `deployment-verification-agent` if PR has migrations
- Output: `todos/*-pending-{p1|p2|p3}-*.md` — P1 findings block merge

**Step 6: `/triage`** — Approve or reject findings (runs on Haiku for speed)
- Presents each finding one by one: severity, scenario, proposed fix, effort
- User says: **yes** (approve) / **next** (skip) / **custom** (modify)
- Output: approved items become `todos/*-ready-*.md`

**Step 7: `/resolve_todo_parallel`** — Fix approved findings
- Spawns `pr-comment-resolver` per todo in parallel
- Commits fixes, marks todos complete
- Also: `/resolve_parallel` (TODO comments in code), `/resolve_pr_parallel` (PR review comments)

**Step 8: `/workflows:compound`** — Capture what was learned
- Spawns 6 parallel subagents: context analyzer, solution extractor, related docs finder, prevention strategist, category classifier, documentation writer
- Output: `docs/solutions/<category>/<symptom>-<module>-YYYYMMDD.md`
- Categories: `performance-issues/`, `database-issues/`, `security-issues/`, `ui-bugs/`, `integration-issues/`, `logic-errors/`, `build-errors/`, `test-failures/`, `runtime-errors/`

**Shortcuts**:
- `/lfg` — Full autonomous loop: plan -> deepen -> work -> review -> resolve -> test
- `/slfg` — Same as `/lfg` but with swarm mode (parallel specialist subagents)
- `/plan_review` — Quick 3-agent plan review (dhh-rails, kieran-rails, code-simplicity)

**Todo lifecycle**:
```
/workflows:review → todos/*-pending-{p1|p2|p3}-*.md
/triage           → todos/*-ready-{p1|p2|p3}-*.md
/resolve_*        → todos/*-complete-{p1|p2|p3}-*.md
```

**File artifacts**:
```
docs/brainstorms/    ← /workflows:brainstorm
docs/plans/          ← /workflows:plan (PROTECTED — never deleted by review)
docs/solutions/      ← /workflows:compound (PROTECTED — knowledge base)
todos/               ← /workflows:review + /triage + /resolve
```

**Combined with superpowers**:

```
superpowers:brainstorming     → clarify what to build
/workflows:plan               → detailed implementation plan
/deepen-plan                  → enhance with research agents
superpowers:subagent-driven   → execute with fresh agents
/workflows:review             → multi-agent review
/workflows:compound           → capture learnings
```

### Quantitative Research Pipeline

The full loop from literature to production:

| Step | Tool | What it does |
|------|------|-------------|
| Literature review | `/paper-reading [path]` | Three-pass reading (5min/30min/60min) via Explore subagent |
| Research spec | `/qrd` | Interactive questionnaire -> structured QRD document with hypothesis, data requirements, acceptance criteria |
| Market data | `/market-data-fetcher [ticker]` | Auto-routes to best source (Stooq for Polish, Yahoo for US, Binance for crypto, FRED for macro) |
| Polish fund data | `analizy-pl-data` | Programmatic access to 2,133 Polish investment funds (FIO/FIZ/FZG) |
| Database queries | `database-explorer` agent | Natural language -> SQL via Sonnet. Schema discovery, query optimization. |
| SQL templates | `/sql-patterns` | Copy-pasteable query templates: time-series, cohort analysis, window functions, CTEs |
| Experiment analysis | `mlflow-analyzer` agent | Lightweight Haiku agent for experiment comparison, hyperparameter sensitivity |
| Model explainability | `shap` skill | SHAP values for tree-based, deep learning, linear, and black-box models |
| Statistical analysis | `statistical-analysis` / `statsmodels` / `pymc` / `scikit-survival` | Test selection, Bayesian modeling, survival analysis |
| Time series ML | `aeon` skill | Classification, regression, clustering, forecasting, anomaly detection |
| Deep learning | `pytorch-lightning` | LightningModules, multi-GPU training, callbacks, logging |
| EDA | `exploratory-data-analysis` | Auto-detect 200+ scientific file formats, generate quality reports |
| Visualization | `@skills/visualization` | matplotlib, seaborn, plotly, networkx, scientific-visualization, umap-learn |
| Documentation | `/readme` | Generate comprehensive project README (runs in forked context) |

**MCP servers used**: `postgres` (database), `firecrawl` (web scraping), `sequential-thinking` (complex reasoning), `memory` (persistent facts)

**Research workflow plugin** (separate from compound-engineering):
- `/research:start <topic>` — Initialize `docs/research/` structure
- `/research:hypothesis "<statement>"` — Document testable hypothesis
- `/research:experiment <name>` — Log experiment with reproducible setup
- `/research:finding "<title>"` — Document validated finding
- `/research:paper <url>` — Extract and analyze papers
- `/research:index` — Show research overview

### Code Quality & Review

**Pre-implementation gate**: `forced-eval` intercepts every prompt and enforces explicit evaluation of available skills, MCP tools, and agents before coding starts. Increases skill activation from ~50% to ~84%.

**Documentation tracking**: `doc-enforcer` monitors Edit/Write tool calls. After 3+ code file edits without touching a doc file, it surfaces a reminder. Configurable via `DOC_ENFORCER_THRESHOLD`.

**Multi-agent review**: `/workflows:review` runs 13+ specialist agents in parallel:

| Agent | Focus |
|-------|-------|
| `security-sentinel` | OWASP Top 10, auth, injection |
| `performance-oracle` | N+1 queries, memory, caching |
| `architecture-strategist` | Component boundaries, coupling |
| `code-simplicity-reviewer` | YAGNI, minimalism (final pass) |
| `data-integrity-guardian` | Migrations, privacy, data safety |
| `schema-drift-detector` | Unrelated schema changes |
| `agent-native-reviewer` | Agent accessibility |
| `pattern-recognition-specialist` | Patterns & anti-patterns |
| `dhh-rails-reviewer` | Rails conventions (DHH style) |
| `kieran-rails-reviewer` | Strict Rails conventions |
| `kieran-python-reviewer` | Strict Python conventions |
| `kieran-typescript-reviewer` | Strict TS conventions |
| `design-implementation-reviewer` | Figma compliance |

Findings are consolidated into priority-ranked todo files: `todos/{issue_id}-pending-{P1|P2|P3}-*.md`

**Commit messages**: `/generating-commit-messages` is mandatory before every git commit. Enforces present-tense imperatives with "why" explanations.

### Session & Context Management

**Strategic compaction**: The `strategic-compact` plugin monitors tool call frequency:

| Threshold | Action |
|-----------|--------|
| 50 tool calls | First reminder to consider `/compact` |
| Every 25 after | Subsequent reminders |
| ~85% context | Urgent warning |

**Two compaction strategies**:
- `/compact` — In-place context summarization. Good after completing a major task or before switching focus.
- `/strategic-compact:handoff <goal>` — Creates structured handoff document at `.claude/handoffs/<timestamp>-<slug>.md` with context summary, key decisions, relevant files, and next steps. Use for explicit session transitions.

**Session persistence**: Automatic save/restore of unfinished work.
- On stop: writes session state to `~/.claude/sessions/`
- On start: surfaces up to 3 unfinished sessions from last 7 days
- `/session-persistence:list` — List saved sessions
- `/session-persistence:load` — Restore a specific session

**Context management skill**: `context-management` is a model-invocable skill (not user-invocable) that Claude auto-applies during long sessions. Strategies: search-before-read, progressive disclosure, save-to-files, context checkpoints.

### Continuing from a Handoff

Start a new session and load the handoff:

```bash
claude
> Read .claude/handoffs/2024-01-15-api-endpoints.md and continue the work
```

The handoff provides context without the full transcript overhead.

### Learning & Self-Improvement

Two distinct learning loops operate in parallel:

**Behavioral learning** (adaptive-learning plugin):

```
Every tool call → observe.py logs to observations.jsonl
                        |
/adaptive-learning:analyze    →  Pattern detection → Create/update instincts
                        |
/insights (native)       →  HTML report with friction patterns, suggestions
                        |
/adaptive-learning:ingest-insights  →  Convert insights → persistent instincts
                        |
Next session start       →  session_start.py surfaces top instincts
                        |
Claude behaves differently →  More observations → cycle continues
```

This learns **Claude's behavioral patterns**: tool sequences, preferences, error-then-fix corrections, project-specific habits. Instincts have confidence scores that grow with confirmation and decay with contradictions.

Commands:
- `/adaptive-learning:status` — View instincts with confidence bars, observation stats
- `/adaptive-learning:analyze [--since] [--dry-run]` — Mine observations for patterns
- `/adaptive-learning:ingest-insights [--dry-run]` — Convert `/insights` report to instincts
- `/adaptive-learning:export` / `/adaptive-learning:import` — Backup/share instinct bundles

**Project knowledge** (compound-engineering):

```
Problem encountered → Solution found
    |
/workflows:compound → docs/solutions/{category}/symptom-module-YYYYMMDD.md
    |
Next /workflows:plan → learnings-researcher agent searches docs/solutions/
    |
/deepen-plan → spawns agents that surface relevant past solutions
    |
Better plan (avoids past mistakes)
```

This learns **project-level engineering knowledge**: categorized solutions with YAML metadata, cross-referenced and searchable. Each solved problem makes the next plan better.

### Output & Sharing

| Command | Output |
|---------|--------|
| `/gist-report` | Converts files/descriptions/sessions to styled HTML -> public GitHub gist with preview link |
| `/gist-transcript` | Current session transcript -> GitHub gist |
| `/notify:send <message>` | Push notification via ntfy.sh |
| `/notify:config` | View/update notification settings |
| `/notify:test` | Send test notification |

## Skill Activation Patterns

### How Skills Activate

Skills activate through three mechanisms:
1. **Explicit invocation**: `/skill-name` — most reliable
2. **Trigger phrases**: Keywords matching the skill's description
3. **Model recognition**: Claude identifies relevant skills from context

### Why `forced-eval` Matters

The `forced-eval` plugin increases skill activation from ~50% to ~84%. It intercepts before implementation and forces: "Should any skill, MCP tool, or agent be used here?"

Without it, Claude may jump to coding without using available structured approaches.

### Chaining Skills

Complex work often chains skills across phases:

```
brainstorm → write-plan → worktree → execute → review → compound
```

Each skill's output feeds the next phase. For quantitative work:

```
paper-reading → qrd → market-data-fetcher → sql-patterns → mlflow-analyzer → readme
```

## Plugin Ecosystem

### Qute Plugins (9)

| Plugin | Events | Commands | Purpose |
|--------|--------|----------|---------|
| adaptive-learning | SessionStart, PostToolUse | status, analyze, export, import, ingest-insights | Observe tool patterns, learn instincts, surface at session start |
| doc-enforcer | PostToolUse | — | Track code vs doc edits, remind when docs need updating |
| forced-eval | UserPromptSubmit | — | Force skill/MCP/agent evaluation before implementation |
| notifications | PostToolUse | send, config, test, gist-report, gist-transcript | Push notifications via ntfy.sh for long-running commands |
| research-workflow | — | start, hypothesis, experiment, finding, paper, index | ML/DS research lifecycle in `docs/research/` |
| ruff-formatter | PostToolUse | — | Auto-format Python files with ruff after edits |
| session-persistence | SessionStart, Stop | list, load | Save/restore session state across sessions |
| skill-use-logger | PostToolUse | — | Log skill invocations to JSONL for analytics |
| strategic-compact | PreToolUse, PreCompact | handoff | Context compaction suggestions + session transitions |

### External Plugins

| Plugin | Source | Description |
|--------|--------|-------------|
| compound-engineering | every-marketplace | 29 agents, 25 commands, 16 skills, 1 MCP — full development lifecycle with knowledge compounding |
| superpowers | claude-plugins-official | Structured planning, brainstorming, TDD, debugging, code review, worktrees |
| context7 | claude-plugins-official | Framework documentation lookup (100+ frameworks) |
| github | claude-plugins-official | GitHub integration |
| commit-commands | claude-plugins-official | Git commit workflow |
| hookify | claude-plugins-official | Hook creation utilities |
| code-simplifier | claude-plugins-official | Code simplification suggestions |
| playground | claude-plugins-official | Experimental features |
| document-skills | anthropic-agent-skills | Document processing skills |
| example-skills | anthropic-agent-skills | Reference skill implementations (frontend-design, web-artifacts, canvas-design, PDF, DOCX, PPTX, etc.) |

### Project-Specific Plugins (quant bundle)

| Plugin | Purpose |
|--------|---------|
| pyright-lsp | Python static type checking |
| feature-dev | Feature development workflow |
| llm-council | Multi-LLM decision-making |
| llm-external-review | External code/design review |

## Skill Inventory

### Foundational

| Skill | Invocation | Purpose |
|-------|------------|---------|
| generating-commit-messages | `/generating-commit-messages` | MANDATORY before commits. Structured messages with present-tense imperatives. |
| worktrees | `/worktrees [branch]` | Parallel development using git worktrees |
| readme | `/readme` | Exhaustive project documentation (forked context) |
| context-management | Model-invocable only | Token budget strategies for long sessions |
| llm-external-review | `/llm-external-review` | Second opinions from Codex/Gemini CLIs |

### Research & Analysis

| Skill | Invocation | Purpose |
|-------|------------|---------|
| paper-reading | `/paper-reading [path]` | Three-pass paper analysis via Explore subagent |
| qrd | `/qrd` | Quantitative Research & Development specification documents |

### Data & Quantitative

| Skill | Invocation | Purpose |
|-------|------------|---------|
| market-data-fetcher | `/market-data-fetcher [ticker]` | Multi-source market data with auto-routing |
| analizy-pl-data | User-invocable | Polish investment fund data (2,133 funds) |
| sql-patterns | `/sql-patterns` | SQL query templates and best practices |
| garmin-health | `/garmin-health [command]` | Health metrics from pre-computed SQLite summaries |

### ML & Statistics (sub-bundles)

**`@skills/ml-core`**: scikit-learn, shap, pytorch-lightning, aeon, exploratory-data-analysis

**`@skills/statistics`**: statsmodels, pymc, scikit-survival, statistical-analysis

**`@skills/visualization`**: matplotlib, seaborn, plotly, networkx, scientific-visualization, umap-learn

**`@skills/research-tools`**: openalex-database, perplexity-search, literature-review, citation-management

**`@skills/data-processing`**: polars, dask, vaex

### Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| research-paper-analyst | Opus | PDF extraction + three-pass reading for papers, reports, prospectuses |
| mlflow-analyzer | Haiku | Experiment comparison, hyperparameter sensitivity, feature direction analysis |
| database-explorer | Sonnet | Natural language -> SQL, schema discovery, query optimization |
| obsidian-knowledge-agent | Sonnet | Knowledge retrieval from Obsidian vault + docs/knowledge/ |

### Branding

| Skill | Purpose |
|-------|---------|
| brand-rockbridge | Rockbridge TFI brand identity (teal #00A19A, Roboto, component patterns) |
| brand-dm-evo | Evo Dom Maklerski brand identity (navy #0C2340, blue accent) |

### Output & Sharing

| Skill | Invocation | Purpose |
|-------|------------|---------|
| gist-report | `/gist-report` | Convert to styled HTML -> GitHub gist with preview link |
| gist-transcript | `/gist-transcript` | Session transcript -> GitHub gist |

## MCP Servers

| Server | Auth Required | Bundles | Purpose |
|--------|---------------|---------|---------|
| memory | No | minimal, quant, webdev | Persistent fact storage |
| sequential-thinking | No | minimal, quant, webdev | Complex multi-step reasoning |
| fetch | No | minimal, quant, webdev | Web content fetching |
| firecrawl | Yes (`FIRECRAWL_API_KEY`) | quant | Web scraping and crawling |
| postgres | Yes (`POSTGRES_CONNECTION_STRING`) | quant | Database access |
| brave-search | Yes (`BRAVE_API_KEY`) | — | Web search |
| chrome-devtools | No | webdev | Browser debugging |
| playwright | No | webdev | Browser automation and testing |
| docker | No | webdev | Container management |
| figma | Yes (`FIGMA_ACCESS_TOKEN`) | webdev | Design file access |
| vercel | No | webdev | Deployment management |

## Context Management

### Search Before Read

Don't read files blindly. Search first:
1. `Grep` for specific patterns
2. `Glob` for file discovery
3. Read only what's relevant

### Progressive Disclosure

1. **Overview**: High-level structure (ls, tree, README)
2. **Sample**: Representative files to understand patterns
3. **Targeted**: Specific files for the task at hand

### Save-to-Files Strategy

Keep the conversation lean by offloading large outputs:

- **Save outputs >100 lines to files** instead of displaying in chat
- **Show summaries** with file paths for reference
- **Periodic checkpoints** at ~60% and ~85% context usage
- **Proactive warnings** before large operations that might bloat context

Example flow:
```
Claude: Analysis complete. Full results saved to ./analysis-results.md (847 lines).
        Summary: 12 critical issues, 34 warnings. See file for details.
```

### When to Use Subagents

Use subagents (`Task` tool) to:
- Protect main context from exploratory searches
- Run parallel investigations
- Isolate research that may not be relevant

## Headless Mode

For non-interactive execution of long-running or automated tasks, use the `-p` flag:

```bash
claude -p "instruction" --allowedTools "Bash,Read,Write,Edit"
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `-p "instruction"` | Pass prompt directly, no interactive mode |
| `--allowedTools "..."` | Grant tool permissions (comma-separated) |
| `--dangerously-skip-permissions` | Skip all permission prompts (use with caution) |
| `--output-format json` | Output as JSON (pipe to file) |
| `--output-format stream-json` | Streaming JSON output |

### Use Cases

**Pipeline integration:**
```bash
claude -p "Run tests and summarize failures" \
  --allowedTools "Bash,Read" \
  --output-format json > test-report.json
```

**Batch documentation updates:**
```bash
claude -p "Update all docstrings in src/ to match the new API" \
  --allowedTools "Read,Edit,Glob,Grep"
```

**Refactoring sweeps:**
```bash
claude -p "Replace all uses of deprecated_func with new_func" \
  --allowedTools "Read,Edit,Grep"
```

### Important Notes

- No interactive prompts — pre-grant permissions via `--allowedTools` or `--dangerously-skip-permissions`
- `--dangerously-skip-permissions` bypasses ALL prompts — use only in trusted, sandboxed environments
- **Gotcha**: `--output-format stream-json` requires `--verbose` when using `-p`
- Output goes to stdout; use redirection for files
- Combine with cron or CI for scheduled tasks
- Consider context limits for large operations

## Quick Reference

### Planning & Execution

| Command | Purpose |
|---------|---------|
| `superpowers:brainstorming` | Clarify requirements before building |
| `superpowers:writing-plans` | Create bite-sized implementation plans |
| `superpowers:executing-plans` | Execute plan with checkpoints |
| `superpowers:subagent-driven-development` | Execute with fresh subagent per task |
| `superpowers:systematic-debugging` | Structured debugging approach |
| `superpowers:test-driven-development` | TDD workflow |
| `superpowers:requesting-code-review` | Pre-merge review |
| `superpowers:using-git-worktrees` | Feature branch isolation |
| `/workflows:plan` | Plan features with research |
| `/workflows:work` | Execute with tracking and worktrees |
| `/workflows:review` | Multi-agent code review |
| `/workflows:compound` | Capture learnings |
| `/lfg` | Full autonomous loop |
| `/slfg` | Swarm-enabled autonomous loop |
| `/deepen-plan` | Enhance plan with parallel research agents |

### Session Management

| Command | Purpose |
|---------|---------|
| `/compact` | In-place context summarization |
| `/strategic-compact:handoff <goal>` | Create handoff document for session transition |
| `/session-persistence:list` | List saved sessions |
| `/session-persistence:load` | Restore previous session |

### Adaptive Learning

| Command | Purpose |
|---------|---------|
| `/adaptive-learning:status` | View instincts, observations, config |
| `/adaptive-learning:analyze [--since] [--dry-run]` | Mine patterns from observations |
| `/adaptive-learning:ingest-insights [--dry-run]` | Convert `/insights` report to instincts |
| `/adaptive-learning:export` | Export instincts to JSON bundle |
| `/adaptive-learning:import` | Import instincts from bundle |

### Research

| Command | Purpose |
|---------|---------|
| `/paper-reading [path]` | Three-pass paper analysis |
| `/qrd` | Quantitative research specification |
| `/research:start <topic>` | Initialize research structure |
| `/research:hypothesis "<statement>"` | Document hypothesis |
| `/research:experiment <name>` | Log experiment |
| `/research:finding "<title>"` | Document finding |

### Data & Output

| Command | Purpose |
|---------|---------|
| `/market-data-fetcher [ticker]` | Fetch market data |
| `/sql-patterns` | SQL query templates |
| `/garmin-health [command]` | Health metrics |
| `/gist-report` | Create shareable HTML report |
| `/gist-transcript` | Save session transcript |
| `/notify:send <message>` | Push notification |

### Work Mode Aliases

| Alias | Purpose |
|-------|---------|
| `claude-dev` | Development mode — code first, explain after |
| `claude-research` | Research mode — read widely, no code until clear |
| `claude-review` | Review mode — thorough reading, severity-based feedback |

## Troubleshooting

### Skills Not Activating

**Symptoms**: Claude jumps to implementation without using relevant skills.

**Solutions**:
1. Enable `forced-eval` plugin
2. Use explicit invocation: `/skill-name`
3. Check skill frontmatter has correct triggers
4. Mention the skill name directly

### Context Exhaustion

**Symptoms**: Claude loses track of earlier discussion, responses become generic.

**Solutions**:
1. Use `/compact` to summarize and free space
2. Delegate research to subagents
3. Break large tasks into separate sessions
4. Use progressive disclosure (don't read everything upfront)

### Lost Work

**Symptoms**: Session ended, unsure what was completed.

**Solutions**:
1. Check `session-persistence` plugin output at session start
2. Use `/gist-transcript` before ending important sessions
3. Review git log for committed changes

### Skill Shows Wrong Behavior

**Symptoms**: Skill does something unexpected or outdated.

**Solutions**:
1. Re-read the skill with `Skill` tool (skills evolve)
2. Check if user instructions conflict with skill
3. Use explicit `/skill-name` to force fresh load

## See Also

- [Getting Started](getting-started.md) - Initial setup
- [Bundles Explained](bundles-explained.md) - Component packaging
- [Plugins Explained](plugins-explained.md) - Runtime hooks and commands
- [Workflow Patterns](workflow-patterns.md) - Superpowers vs Compound workflows comparison
