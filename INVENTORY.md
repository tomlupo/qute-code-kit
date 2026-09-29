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

## Skills (10, grouped by directory under `claude/skills/`)

### Quant / data (`quant/`, 5)

| Name | Description |
|---|---|
| `analizy-pl-data` | Programmatic access to Polish investment fund data from analizy.pl |
| `atlasetf-scraper` | Scrape ETF data from atlasetf.pl (screener of ~13k funds, per-ISIN detail, prices) via its JSON API |
| `gpw-benchmark-scraper` | Scrape gpwbenchmark.pl (WIBID/WIBOR reference rates, index list with ISINs, per-index OHLC history) |
| `market-datasets` | Fetch market data from Stooq, NBP, Yahoo, FRED, Tiingo, CCXT, FinancialData |
| `pipeline-docs` | 4-doc pattern (instruction / dataset / methodology / reference) |

### Engineering (`engineering/`, 1)

| Name | Description |
|---|---|
| `skill-assessment` | Audit every skill in one run against Anthropic's skill engineering guide: categories, a coverage matrix, gaps. The estate-wide half; `/qute-essentials:skills improve` scores and patches one skill (TOM-1126). Kept by decision, 2026-09-29 |

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

### Moved to qute-research 2026-09-28 (TOM-1221)

`acceptance-gates`, `investment-research` (now its method protocols),
`research-refute`, `-reproduce`, `-robustness`, `-sweep`, `-bakeoff` — see the
qute-research README in `tomlupo/qute-plugins`. On 2026-09-29 the last two
followed: `investment-research-dashboard` is its `research-dashboard` skill (the
`reporting/` library and its contract tests), and `investment-research-formal`'s
METHODOLOGY skeleton, MiFID II mapping and literature note are its
`research/references/methodology-document.md`. The kit carries no research
skills.

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
| `templates/docs/agents-issue-tracker.md` | Tracker binding starter (`docs/agents/issue-tracker.md`; machine marker + Linear/GitHub division) |
| `templates/WORKFLOW.md` | Symphony/Elixir-style orchestrator contract (frontmatter + agent prompt routing Matt + qute + docs/agents) |
| `templates/docs/prd-template.md` | Product requirements doc starter |
| `templates/docs/tech-spec-template.md` | Technical specification starter |
| `templates/docs/user-flows-template.md` | User flows / journey starter |
| `templates/pyproject/quant-uv.toml` | Quant `pyproject.toml` (uv + ruff + pyright + pytest, per [osquant 2025](https://osquant.com/papers/python-tooling-in-2025/)) |
| `templates/pyproject/webdev-uv.toml` | Webdev `pyproject.toml` (same stack) |
| `templates/settings/*.json` | Settings starters (mirror of `claude/settings/`) |
