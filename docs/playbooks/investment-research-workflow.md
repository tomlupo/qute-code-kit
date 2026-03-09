# Investment Research Workflow

> End-to-end pattern: question → data → analysis → deliverable

## When to Use

Starting a new investment research question — factor analysis, fund comparison, market regime study, strategy backtest, or any structured financial investigation.

## Skills Used

| Skill | Role |
|-------|------|
| `investment-research` | Lifecycle framework (question → data → analysis → deliverable) |
| `investment-research-formal` | Auditable tracking with hypothesis/experiment/finding |
| `paper-reading` | Extract insights from papers, fund cards, prospectuses |
| `investment-research-dashboard` | Self-contained Plotly.js HTML dashboards |
| `market-datasets` | Multi-source data fetching |
| `gist-report` | Shareable HTML report via gist |

## Workflow

### Phase 1: Frame the Question

Use `/investment-research` to structure the research question:

```
/investment-research "Does momentum factor work in Polish equity funds?"
```

This produces a research plan with:
- Clear hypothesis
- Required data sources
- Analysis approach
- Expected deliverable format

### Phase 2: Gather Data

Fetch relevant data using `market-datasets`:
- Price data from Stooq/Yahoo/CCXT
- Fundamentals from relevant sources
- Fund data from analizy.pl if Polish funds

Read relevant literature with `/paper-reading`:
- Academic papers on the factor
- Fund prospectuses and factsheets
- Prior research in `docs/papers/`

### Phase 3: Analyze

For exploratory work:
- Work in `scratch/{study-name}/`
- Build analysis scripts iteratively
- Save intermediate results to files, not conversation

For formal research (publishable, auditable):
- Use `/investment-research-formal` to track hypotheses, experiments, findings
- Each experiment gets a documented result
- Findings link back to specific experiments

### Phase 4: Deliver

Choose deliverable format based on audience:

**Interactive dashboard** (self-serve exploration):
```
/investment-research-dashboard
```
Produces a self-contained HTML file with Plotly.js charts — no server needed.

**Shareable report** (stakeholder communication):
```
/gist-report
```
Styled HTML report via GitHub Gist with preview link.

**Research study** (permanent reference):
Promote from `scratch/` to `research/{study-name}/` with co-located scripts, data, and docs.

### Phase 5: Archive

- Move completed work from `scratch/` to appropriate permanent location
- Update `TASKS.md` (move to Completed)
- If formal: ensure all hypotheses have findings documented
- Link from relevant docs if the study becomes foundational

## Example: Momentum in Polish Equity Funds

```
1. /investment-research "momentum factor in Polish equity funds"
2. Fetch 5-year monthly returns from Stooq for WIG components
3. Fetch fund NAVs from analizy.pl for equity funds
4. /paper-reading on Jegadeesh & Titman (1993), local momentum studies
5. Build factor portfolios in scratch/momentum-pl/
6. /investment-research-dashboard for interactive factor analytics
7. /gist-report for stakeholder summary
8. Promote to research/momentum-pl/ if foundational
```

## Tips

- Start with `/investment-research` even for informal studies — it forces clear thinking
- Use formal tracking (`/investment-research-formal`) when results might be challenged
- Always save large outputs to files — keep conversation context for decisions
- Dashboard skill produces single HTML files — easy to email or share
