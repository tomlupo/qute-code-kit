# Kit inventory

Full contents of `claude/` and `templates/`. Use this as the complete catalog, not as an install-all recommendation. For lean target repos, copy only the bundle or individual tools you need.

## Recommended bundles

These are conceptual bundles for choosing from the personal kit. They do not duplicate files yet; they define the target grouping.

| Bundle | Use when | Likely components |
|---|---|---|
| `quant-research` | Research/lab repos | `investment-research`, `investment-research-formal`, `paper-reading`, `market-datasets`, `backtest`, `qrd`, `investment-research-dashboard` |
| `advisory-production` | Model portfolio / fund-selection / advisory production repos | `pipeline-docs`, `qrd`, `analizy-pl-data`, `investment-research-formal`, `brand-dm-evo`, selected review/reporting tools |
| `python-engineering` | Python libraries, pipelines, tools | `python-patterns`, `sql-patterns`, `code-quality`, `llm-external-review`, `gist-report` |
| `web-product` | Web apps and dashboards | `ui-ux-pro-max`, `architecture-diagram`, `excalidraw`, browser/devtools MCP configs |
| `visual-design` | Presentation, diagram, UI, brand work | `architecture-diagram`, `excalidraw`, `image-generator`, brand skills |

Default rule: do not copy the whole kit into a repo. Install `qute-essentials`, install Matt skills, then copy only the specialist bundle pieces that match the repo.

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
| `templates/qute-agent.yml` | Repo policy for Matt-compatible qute runtime mode |
| `templates/docs/agents-task-tracking.md` | Repo-local `docs/agents/task-tracking.md` starter |
| `templates/docs/adr-template.md` | ADR (architectural decision record) starter |
| `templates/docs/prd-template.md` | Product requirements doc starter |
| `templates/docs/tech-spec-template.md` | Technical specification starter |
| `templates/docs/user-flows-template.md` | User flows / journey starter |
| `templates/pyproject/quant-uv.toml` | Quant `pyproject.toml` (uv + ruff + pyright + pytest, per [osquant 2025](https://osquant.com/papers/python-tooling-in-2025/)) |
| `templates/pyproject/webdev-uv.toml` | Webdev `pyproject.toml` (same stack) |
