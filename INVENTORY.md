# Kit inventory

Full contents of `claude/` and `templates/`. Use as a map — copy the bits you
want into target repos. See [`README.md`](README.md) for the high-level intro
and copy commands.

> The `qute-essentials` plugin (guards, hooks, `/ship`, `/qute-review`,
> research-regime skills) is **not** in this inventory — it moved to
> `tomlupo/qute-platform` (`agent-kit/plugins/qute-essentials/`) on 2026-07-29.

## Skills (33, grouped by directory under `claude/skills/`)

### Quant / research (`quant/`, 14)

| Name | Description |
|---|---|
| `acceptance-gates` | Statistical acceptance gates — deflated Sharpe (DSR), Newey-West HAC t-stat, factor decomposition |
| `analizy-pl-data` | Programmatic access to Polish investment fund data from analizy.pl |
| `atlasetf-scraper` | Scrape ETF data from atlasetf.pl (screener of ~13k funds, per-ISIN detail, prices) via its JSON API |
| `backtest` | Portfolio allocation backtesting via vectorbt (drift, rebalancing, fees, multi-strategy) |
| `bird-twitter` | Retrieve Twitter/X bookmarks and search tweets via Bird CLI |
| `gpw-benchmark-scraper` | Scrape gpwbenchmark.pl (WIBID/WIBOR reference rates, index list with ISINs, per-index OHLC history) |
| `investment-research` | Iterative investment research from question to deliverable |
| `investment-research-formal` | Structured, auditable research with hypotheses + evidence chain |
| `investment-research-dashboard` | Self-contained (offline, no CDN) Plotly HTML dashboards for finance; bundles the canonical `reporting/` lib (`base`/`backtest_dashboard`/`research_story`), reuse-first |
| `market-datasets` | Fetch market data from Stooq, NBP, Yahoo, FRED, Tiingo, CCXT, FinancialData |
| `paper-reading` | Active reading and analysis of research papers |
| `pipeline-docs` | 4-doc pattern (instruction / dataset / methodology / reference) |
| `qrd` | Quantitative Research & Development spec documents |
| `quant-review` | Pre-PR review orchestrator for quant / data-pipeline code (path-routed scoped reviewers) |

### Multi-agent research workflows (`research/`, 5)

Symlinked into `~/.claude/skills/` — each fans out a multi-agent Workflow.

| Name | Description |
|---|---|
| `research-bakeoff` | Tournament: implement + evaluate N candidate approaches in parallel worktrees, pick a winner |
| `research-refute` | Adversarial panel of skeptics, each attacking a finding via a different failure mode |
| `research-reproduce` | Reproduce a result via independent paths (implementation / inputs / library), cross-check |
| `research-robustness` | Stress a method across windows × regimes × parameters; collect a robustness grid |
| `research-sweep` | Multi-modal evidence sweep (own data, benchmarks, atlas notes, literature, code) + cited synthesis |

### Engineering / quality (`engineering/`, 7 + the `workflow` bundle)

| Name | Description |
|---|---|
| `code-quality` | Blunt critique + static checks + domain-specific patterns |
| `debug-session` | Runbook for diagnosing Claude Code session problems |
| `gist-report` | Create a shareable HTML report (or upload a session transcript) and return a preview link |
| `llm-external-review` | Get second opinions from Codex, Gemini via their CLIs |
| `python-patterns` | Idiomatic Python patterns reference |
| `skill-assessment` | Audit skills against Anthropic's skill engineering guide |
| `sql-patterns` | SQL query patterns and templates |
| `workflow/` | PRD → slice → PR pipeline bundle (5 sub-skills: `grill`, `to-prd`, `to-slices`, `tdd`, `triage`), adapted from mattpocock/skills |

### Visual / UX (`visual/`, 4)

| Name | Description |
|---|---|
| `architecture-diagram` | Dark-themed system architecture diagrams as standalone HTML |
| `excalidraw` | Hand-drawn diagrams as Excalidraw JSON files |
| `image-generator` | Generate and edit images via Google Gemini API |
| `ui-ux-pro-max` | UI/UX design intelligence for web and mobile |

### Brand (`brand/`, 3)

| Name | Description |
|---|---|
| `brand-dm-evo` | Evo Dom Maklerski brand identity for web/PDF |
| `brand-rockbridge` | Rockbridge TFI brand identity for web/PDF |
| `brand-sonte` | Sonte smart-film brand identity for React/Tailwind/CSS frontend work |

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

## Root-file starters (2)

| File | Use case |
|---|---|
| `claude/root-files/CLAUDE.md` | Root CLAUDE.md starter |
| `claude/root-files/AGENTS.md` | Root AGENTS.md starter |

## Templates

| Path | Use case |
|---|---|
| `templates/docs/adr-template.md` | ADR (architectural decision record) starter |
| `templates/docs/agents-research-workflow.md` | Standard research regime for lab repos (`docs/agents/research-workflow.md` starter) |
| `templates/docs/agents-issue-tracker.md` | Tracker binding starter (`docs/agents/issue-tracker.md`; machine marker + Linear/GitHub division) |
| `templates/WORKFLOW.md` | Symphony/Elixir-style orchestrator contract (frontmatter + agent prompt routing Matt + qute + docs/agents) |
| `templates/docs/prd-template.md` | Product requirements doc starter |
| `templates/docs/tech-spec-template.md` | Technical specification starter |
| `templates/docs/user-flows-template.md` | User flows / journey starter |
| `templates/pyproject/quant-uv.toml` | Quant `pyproject.toml` (uv + ruff + pyright + pytest, per [osquant 2025](https://osquant.com/papers/python-tooling-in-2025/)) |
| `templates/pyproject/webdev-uv.toml` | Webdev `pyproject.toml` (same stack) |
| `templates/research/` | Canonical research pin gate `check_research_pins.py` (provenance-on-conclude; unit-tested in `tests/`) + research-line `_template/` |
| `templates/settings/*.json` | Settings starters (mirror of `claude/settings/`) |
