# Kit inventory

Full contents of `claude/` and `templates/`. Use as a map — copy the bits you want into target repos. See [`README.md`](README.md) for the high-level intro and copy commands.

## Skills (24)

### Quant / research

| Name | Description |
|---|---|
| `analizy-pl-data` | Programmatic access to Polish investment fund data from analizy.pl |
| `atlasetf-scraper` | Scrape ETF data from atlasetf.pl (screener of ~13k funds, per-ISIN detail, prices) via its JSON API |
| `backtest` | Portfolio allocation backtesting via vectorbt (drift, rebalancing, fees, multi-strategy) |
| `bird-twitter` | Retrieve Twitter/X bookmarks and search tweets via Bird CLI |
| `investment-research` | Iterative investment research from question to deliverable |
| `investment-research-formal` | Structured, auditable research with hypotheses + evidence chain |
| `investment-research-dashboard` | Self-contained Plotly.js HTML dashboards for finance |
| `market-datasets` | Fetch market data from Stooq, NBP, Yahoo, FRED, Tiingo, CCXT, FinancialData |
| `paper-reading` | Active reading and analysis of research papers |
| `pipeline-docs` | 4-doc pattern (instruction / dataset / methodology / reference) |
| `qrd` | Quantitative Research & Development spec documents |

### Engineering / quality

| Name | Description |
|---|---|
| `code-quality` | Blunt critique + static checks + domain-specific patterns |
| `debug-session` | Runbook for diagnosing Claude Code session problems |
| `python-patterns` | Idiomatic Python patterns reference |
| `sql-patterns` | SQL query patterns and templates |
| `skill-assessment` | Audit skills against Anthropic's skill engineering guide |
| `llm-external-review` | Get second opinions from Codex, Gemini via their CLIs |
| `gist-report` | Create a shareable HTML report (or upload a session transcript) and return a preview link |

### Visual / UX / brand

| Name | Description |
|---|---|
| `architecture-diagram` | Dark-themed system architecture diagrams as standalone HTML |
| `excalidraw` | Hand-drawn diagrams as Excalidraw JSON files |
| `image-generator` | Generate and edit images via Google Gemini API |
| `ui-ux-pro-max` | UI/UX design intelligence for web and mobile |
| `brand-dm-evo` | Evo Dom Maklerski brand identity for web/PDF |
| `brand-rockbridge` | Rockbridge TFI brand identity for web/PDF |

## Agents (2)

| Name | Description |
|---|---|
| `data-pipeline-debugger` | Debug data pipelines (input/output validation, root-cause tracing) |
| `research-synthesizer` | Synthesize findings across multiple papers / studies |

## MCP server configs (7)

| Server | Use case |
|---|---|
| `chrome-devtools` | Browser automation via Chrome DevTools |
| `docker` | Docker container management |
| `figma` | Figma design file access |
| `firecrawl` | Web scraping (`FIRECRAWL_API_KEY`) |
| `playwright` | Browser automation via Playwright |
| `postgres` | Postgres database (`POSTGRES_CONNECTION_STRING`) |
| `vercel` | Vercel deploy/admin |

## Settings templates (3)

| Template | Use case |
|---|---|
| `global-generic.json` | Liberal defaults for personal `~/.claude/settings.json` |
| `project-quant.json` | Quant-project permissions (Edit/Write src/, notebooks/, models/...) |
| `project-webdev.json` | Webdev-project permissions |

## Templates

| Path | Use case |
|---|---|
| `templates/docs/adr-template.md` | ADR (architectural decision record) starter |
| `templates/docs/agents-research-workflow.md` | Standard research regime for lab repos (`docs/agents/research-workflow.md` starter) |
| `templates/docs/prd-template.md` | Product requirements doc starter |
| `templates/docs/tech-spec-template.md` | Technical specification starter |
| `templates/docs/user-flows-template.md` | User flows / journey starter |
| `templates/pyproject/quant-uv.toml` | Quant `pyproject.toml` (uv + ruff + pyright + pytest, per [osquant 2025](https://osquant.com/papers/python-tooling-in-2025/)) |
| `templates/pyproject/webdev-uv.toml` | Webdev `pyproject.toml` (same stack) |
