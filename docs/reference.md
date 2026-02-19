# Reference

Complete inventory of skills, agents, plugins, and MCP servers.

## Skills

### Custom Skills

| Skill | Plugin | Invocation | Notes |
|-------|--------|------------|-------|
| generating-commit-messages | minimal, quant | `/generating-commit-messages` | Mandatory before commits |
| worktrees | minimal | `/worktrees [branch]` | Git worktree management |
| readme | minimal | `/readme` | README generation (`context: fork`) |
| llm-external-review | minimal | `/llm-external-review` | Second opinions from Codex/Gemini |
| context-management | quant, webdev | Auto | Token budget strategies (`user-invocable: false`) |
| paper-reading | quant | `/paper-reading [path]` | Three-pass analysis (`agent: Explore`) |
| sql-patterns | quant | `/sql-patterns` | SQL templates and best practices |
| market-data-fetcher | quant | `/market-data-fetcher [ticker]` | Multi-source market data |
| qrd | quant | `/qrd` | Quant R&D specification documents |
| gist-report | quant, webdev | `/gist-report` | HTML reports via GitHub gist |
| gist-transcript | quant, webdev | `/gist-transcript` | Session transcript gist |
| pdf-skill | webdev | `/pdf-skill` | PDF text/image/table extraction |
| garmin-health | standalone | `/garmin-health [command]` | Health metrics from SQLite |
| analizy-pl-data | standalone | `/analizy-pl-data` | Polish fund data (2,133 funds) |
| brand-dm-evo | project-specific | — | Evo Dom Maklerski brand identity |
| brand-rockbridge | project-specific | — | Rockbridge TFI brand identity |

### External Skills (curated)

| Skill | Sub-bundle | Plugin |
|-------|------------|--------|
| scikit-learn | `@skills/ml-core` | quant |
| shap | `@skills/ml-core` | quant |
| pytorch-lightning | `@skills/ml-core` | quant |
| aeon | `@skills/ml-core` | quant |
| exploratory-data-analysis | `@skills/ml-core` | quant |
| statsmodels | `@skills/statistics` | quant |
| pymc | `@skills/statistics` | quant |
| matplotlib | `@skills/visualization` | quant |
| plotly | `@skills/visualization` | quant |
| polars | `@skills/data-processing` | quant |
| context7 | — | — |
| dignified-python-313 | — | — |

### Sub-bundles

For use with `--add @skills/<name>`:

| Sub-bundle | Skills |
|------------|--------|
| `ml-core` | scikit-learn, shap, pytorch-lightning, aeon, EDA |
| `statistics` | statsmodels, pymc |
| `visualization` | matplotlib, plotly |
| `data-processing` | polars |

## Agents

| Agent | Plugin | Model | Skills | Notes |
|-------|--------|-------|--------|-------|
| research-paper-analyst | quant | opus | paper-reading | PDF analysis + structured reading |
| mlflow-analyzer | quant | haiku | mlflow, shap | Experiment comparison |
| python-reviewer | quant | sonnet | dignified-python-313 | Python 3.13 code review |
| database-explorer | standalone | sonnet | sql-patterns | SQL via postgres MCP |
| obsidian-knowledge | standalone | sonnet | — | Knowledge retrieval via obsidian MCP |
| frontend-designer | webdev | sonnet | — | Design mockups to component specs |
| code-refactorer | webdev | sonnet | — | Improve structure, preserve behavior |
| prd-writer | webdev | sonnet | — | Product requirements documents |
| security-auditor | webdev | sonnet | — | Codebase security audits |
| project-task-planner | webdev | sonnet | — | Development task lists from PRDs |

## Plugins

### Profile Plugins

| Plugin | Skills | Agents | Hooks |
|--------|:------:|:------:|:-----:|
| qute-minimal | 4 | — | — |
| qute-quant | 17 | 3 | post-commit changelog |
| qute-webdev | 4 | 5 | — |

### Utility Plugins

| Plugin | Events | Commands |
|--------|--------|----------|
| forced-eval | UserPromptSubmit | — |
| strategic-compact | PreToolUse, PreCompact | handoff |
| doc-enforcer | PostToolUse | — |
| ruff-formatter | PostToolUse | — |
| skill-use-logger | PostToolUse | — |
| session-persistence | SessionStart, Stop | list, load |
| notifications | PostToolUse | send, config, test |
| adaptive-learning | SessionStart, PostToolUse | status, analyze, export, import, ingest-insights |
| research-workflow | — | start, hypothesis, experiment, finding, paper, index |

### External Plugins

| Plugin | Source | Description |
|--------|--------|-------------|
| compound-engineering | every-marketplace | 29 agents, 25 commands, 16 skills — full dev lifecycle |
| superpowers | claude-plugins-official | Structured planning, TDD, debugging, code review |
| context7 | claude-plugins-official | Live framework docs |
| github | claude-plugins-official | GitHub integration |
| commit-commands | claude-plugins-official | Git commit workflow |
| hookify | claude-plugins-official | Hook creation utilities |
| code-simplifier | claude-plugins-official | Code simplification |
| playground | claude-plugins-official | Experimental features |
| pyright-lsp | claude-plugins-official | Python type checking |
| feature-dev | claude-plugins-official | Feature development workflow |
| frontend-design | claude-plugins-official | Frontend design workflow |

## MCP Servers

| Server | Auth | Bundle | Purpose |
|--------|:----:|--------|---------|
| fetch | — | minimal | Web content fetching |
| sequential-thinking | — | minimal | Multi-step reasoning |
| memory | — | minimal | Persistent fact storage |
| firecrawl | `FIRECRAWL_API_KEY` | quant | Web scraping |
| postgres | `POSTGRES_CONNECTION_STRING` | quant | Database access |
| brave-search | `BRAVE_API_KEY` | — | Web search |
| vercel | — | webdev | Deployment management |
| chrome-devtools | — | webdev | Browser debugging |
| playwright | — | webdev | Browser automation |
| docker | — | webdev | Container management |
| figma | `FIGMA_ACCESS_TOKEN` | webdev | Design file access |

## Hook Events

| Event | When it fires |
|-------|-------------|
| `SessionStart` | Session begins |
| `UserPromptSubmit` | User sends a message |
| `PreToolUse` | Before any tool call |
| `PostToolUse` | After any tool call |
| `PreCompact` | Before context compaction |
| `Stop` | Session ends |

## Environment Variables

| Variable | Used by | Default |
|----------|---------|---------|
| `CLAUDE_SESSION_ID` | All session-scoped plugins | — |
| `CLAUDE_PLUGIN_ROOT` | All plugin scripts | — |
| `DOC_ENFORCER_THRESHOLD` | doc-enforcer | 3 |
| `COMPACT_THRESHOLD` | strategic-compact | 50 |
| `COMPACT_INTERVAL` | strategic-compact | 25 |
