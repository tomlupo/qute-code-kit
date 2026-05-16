# qute-code-kit

Personal Claude Code kit and a distributable plugin, in one repo:

- **`claude/`** — personal library of skills, agents, MCP configs, and settings. Browse, copy what you need into target repos.
- **`plugins/qute-essentials/`** — distributable Claude Code plugin shipped via the marketplace.

```bash
# Install the plugin
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace

# Copy a kit component into a project
cp -r ~/projects/qute-code-kit/claude/skills/paper-reading ~/projects/myrepo/.claude/skills/
```

## Plugin: `qute-essentials`

Hooks, security guards, and universal skills. See [`plugins/qute-essentials/README.md`](plugins/qute-essentials/README.md) for full coverage. Quick map:

| Type | Components |
|------|------------|
| Hooks | ruff-formatter, doc-reminder, skill-use-logger, ntfy notifications, auto-audit |
| Guards | destructive, malware, secrets, audit, lakera, langfuse |
| Skills | `/ship`, `/handoff`, `/pickup`, `/board`, `/issue`, `/status`, `/audit`, `/test`, `/guard`, `/config`, `/decision`, `/gbu`, `/wtf`, `/readme`, `/worktrees`, `generating-commit-messages` |

```bash
claude plugin install qute-essentials@qute-marketplace
```

## Kit inventory

### Skills (26)

#### Quant / research

| Name | Description |
|---|---|
| `analizy-pl-data` | Programmatic access to Polish investment fund data from analizy.pl |
| `backtest` | Portfolio allocation backtesting via vectorbt (drift, rebalancing, fees, multi-strategy) |
| `bird-twitter` | Retrieve Twitter/X bookmarks and search tweets via Bird CLI |
| `investment-research` | Iterative investment research from question to deliverable |
| `investment-research-formal` | Structured, auditable research with hypotheses + evidence chain |
| `investment-research-dashboard` | Self-contained Plotly.js HTML dashboards for finance |
| `market-datasets` | Fetch market data from Stooq, NBP, Yahoo, FRED, Tiingo, CCXT, FinancialData |
| `paper-reading` | Active reading and analysis of research papers |
| `pipeline-docs` | 4-doc pattern (instruction / dataset / methodology / reference) |
| `qrd` | Quantitative Research & Development spec documents |

#### Engineering / quality

| Name | Description |
|---|---|
| `code-quality` | Blunt critique + static checks + domain-specific patterns |
| `debug-session` | Runbook for diagnosing Claude Code session problems |
| `python-patterns` | Idiomatic Python patterns reference |
| `sql-patterns` | SQL query patterns and templates |
| `skill-assessment` | Audit skills against Anthropic's skill engineering guide |
| `llm-external-review` | Get second opinions from Codex, Gemini via their CLIs |

#### Visual / UX / brand

| Name | Description |
|---|---|
| `architecture-diagram` | Dark-themed system architecture diagrams as standalone HTML |
| `excalidraw` | Hand-drawn diagrams as Excalidraw JSON files |
| `image-generator` | Generate and edit images via Google Gemini API |
| `ui-ux-pro-max` | UI/UX design intelligence for web and mobile |
| `brand-dm-evo` | Evo Dom Maklerski brand identity for web/PDF |
| `brand-rockbridge` | Rockbridge TFI brand identity for web/PDF |

#### Workflow / context

| Name | Description |
|---|---|
| `gist-report` | Create a shareable HTML report and return a preview link |
| `gist-transcript` | Upload the current Claude Code session transcript as a GitHub Gist |
| `project-seed` | Seed a new repo from Obsidian vault specs |
| `vault-access` | Read project context from the Obsidian vault |

### Agents (2)

| Name | Description |
|---|---|
| `data-pipeline-debugger` | Debug data pipelines (input/output validation, root-cause tracing) |
| `research-synthesizer` | Synthesize findings across multiple papers / studies |

### MCP server configs (7)

| Server | Use case |
|---|---|
| `chrome-devtools` | Browser automation via Chrome DevTools |
| `docker` | Docker container management |
| `figma` | Figma design file access |
| `firecrawl` | Web scraping (`FIRECRAWL_API_KEY`) |
| `playwright` | Browser automation via Playwright |
| `postgres` | Postgres database (`POSTGRES_CONNECTION_STRING`) |
| `vercel` | Vercel deploy/admin |

### Settings templates (3)

| Template | Use case |
|---|---|
| `global-generic.json` | Liberal defaults for personal `~/.claude/settings.json` |
| `project-quant.json` | Quant-project permissions (Edit/Write src/, notebooks/, models/...) |
| `project-webdev.json` | Webdev-project permissions |

### Templates

| Path | Use case |
|---|---|
| `templates/docs/adr-template.md` | ADR (architectural decision record) starter |
| `templates/docs/prd-template.md` | Product requirements doc starter |
| `templates/docs/tech-spec-template.md` | Technical specification starter |
| `templates/docs/user-flows-template.md` | User flows / journey starter |
| `templates/pyproject/quant-uv.toml` | Quant `pyproject.toml` (pandas, numpy, mlflow, jupyter) |
| `templates/pyproject/webdev-uv.toml` | Webdev `pyproject.toml` |

### Docs

- `docs/playbooks/` — multi-step workflows (compound engineering, multi-agent review, investment research, session continuity, ...)
- `docs/cheatsheets/` — Claude CLI, prompt engineering, XML prompting
- `docs/prompts/` — reusable prompt patterns
- `docs/reference.md`, `docs/resources.md` — curated external links

## How to use the kit

Pick what you need; copy by hand.

```bash
# Skill — copy directory into target repo
cp -r ~/projects/qute-code-kit/claude/skills/paper-reading ~/projects/myrepo/.claude/skills/

# Agent — single file
cp ~/projects/qute-code-kit/claude/agents/research-synthesizer.md ~/projects/myrepo/.claude/agents/

# MCP config
mkdir -p ~/projects/myrepo/.mcp/firecrawl
cp ~/projects/qute-code-kit/claude/mcp/firecrawl.json ~/projects/myrepo/.mcp/firecrawl/.mcp.json

# Settings
cp ~/projects/qute-code-kit/claude/settings/project-quant.json ~/projects/myrepo/.claude/settings.json

# Doc template
cp ~/projects/qute-code-kit/templates/docs/adr-template.md ~/projects/myrepo/docs/decisions/0001-foo.md
```

For new repos that need release tooling, install the plugin and use `/ship` (it handles commitizen + CHANGELOG + tag) plus `/ship`'s auto-setup (first-run only).

## Releasing the plugin

```bash
scripts/release-plugin.sh qute-essentials <patch|minor|major|X.Y.Z>
git push --follow-tags
```

See `CLAUDE.md` for repo conventions and the canonical-manifest model.
