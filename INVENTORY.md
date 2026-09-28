# Kit inventory

Full contents of `claude/` and `templates/`. Use as a map — copy the bits you
want into target repos. See [`README.md`](README.md) for the high-level intro
and copy commands.

> **Not in this inventory.** The `qute-essentials` plugin (guards, hooks, the
> session loop, `/pr`, `/ship`) and the `qute-research` plugin (the research
> lifecycle: `research`, `finding`, `promote`, `quant-review`) live in
> `tomlupo/qute-plugins`. Skills bound to one project live in that project's
> repo, which is their master: the dm-evo fund-selection chain and
> `etf-universe-screening` in dm-evo-lab, `backtest` and `evo-dm-brand` in
> dm-evo-core, `brand-rockbridge` in robo-lab (moved out 2026-09-28, TOM-1235).

**What belongs here:** a skill whose content is not bound to one project.
Being used by a single project today is fine; being written for one is not.
A repo that copies a kit skill stamps it with `PROVENANCE.yaml` (source path,
source commit, each file `tracked` or `forked from <sha>, reason: …`) so the
copy's drift can be checked.

## Skills (19, grouped by directory under `claude/skills/`)

### Quant / data (`quant/`, 9)

| Name | Description |
|---|---|
| `acceptance-gates` | Statistical acceptance gates — deflated Sharpe (DSR), Newey-West HAC t-stat, factor decomposition. Moving to qute-research as engine-neutral gates (TOM-1221) |
| `analizy-pl-data` | Programmatic access to Polish investment fund data from analizy.pl |
| `atlasetf-scraper` | Scrape ETF data from atlasetf.pl (screener of ~13k funds, per-ISIN detail, prices) via its JSON API |
| `gpw-benchmark-scraper` | Scrape gpwbenchmark.pl (WIBID/WIBOR reference rates, index list with ISINs, per-index OHLC history) |
| `investment-research` | Iterative investment research from question to deliverable. Moving to qute-research as a method protocol (TOM-1221) |
| `investment-research-formal` | Structured, auditable research with hypotheses + evidence chain. Moving to qute-research (TOM-1221) |
| `investment-research-dashboard` | Self-contained (offline, no CDN) Plotly HTML dashboards for finance; bundles the canonical `reporting/` lib (`base`/`backtest_dashboard`/`research_story`), reuse-first |
| `market-datasets` | Fetch market data from Stooq, NBP, Yahoo, FRED, Tiingo, CCXT, FinancialData |
| `pipeline-docs` | 4-doc pattern (instruction / dataset / methodology / reference) |

### Multi-agent research workflows (`research/`, 5)

Each fans out a multi-agent Workflow. Moving to qute-research with agent types
that exist where they run (TOM-1221 slice 3).

| Name | Description |
|---|---|
| `research-bakeoff` | Tournament: implement + evaluate N candidate approaches in parallel worktrees, pick a winner |
| `research-refute` | Adversarial panel of skeptics, each attacking a finding via a different failure mode |
| `research-reproduce` | Reproduce a result via independent paths (implementation / inputs / library), cross-check |
| `research-robustness` | Stress a method across windows × regimes × parameters; collect a robustness grid |
| `research-sweep` | Multi-modal evidence sweep (own data, benchmarks, atlas notes, literature, code) + cited synthesis |

### Engineering (`engineering/`, 1)

| Name | Description |
|---|---|
| `skill-assessment` | Audit skills against Anthropic's skill engineering guide. Folds into the `/skills` command (TOM-1126) |

### Visual / UX (`visual/`, 4)

| Name | Description |
|---|---|
| `architecture-diagram` | Dark-themed system architecture diagrams as standalone HTML (vendored, Cocoon AI) |
| `image-generator` | Generate and edit images via Google Gemini API |
| `motion-reel` | Motion-graphics films rendered as code: one JS function of time, headless Chrome with motion blur, a numpy score from the same cue sheet, ffmpeg |
| `ui-ux-pro-max` | UI/UX design intelligence for web and mobile (vendored, nextlevelbuilder) |

### Retired 2026-09-28 (TOM-1235)

Unused, broken, or covered elsewhere; in git history if ever needed:
`bird-twitter`, `code-quality`, `debug-session`, `excalidraw`, `gist-report`,
`llm-external-review`, `paper-reading`, `python-patterns`, `qrd`,
`quant-review` (qute-research owns it), `sql-patterns`, the `workflow/` bundle
(`grill`, `tdd`, `triage`, `to-prd`, `to-slices`; Matt Pocock's plugin owns
them, and qute-essentials depends on it), `brand-sonte` (archived project).

## Agents (2)

| Name | Description |
|---|---|
| `data-pipeline-debugger` | Debug data pipelines (input/output validation, root-cause tracing) |
| `research-synthesizer` | Synthesize findings across multiple papers / studies |

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
