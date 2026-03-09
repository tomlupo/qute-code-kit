---
name: investment-research
description: Guides investment research projects from question through data, analysis, and deliverable. Use when starting a new research topic (portfolio construction, risk analysis, factor studies, asset allocation, fund analysis), when structuring a research directory, or when the user mentions research, backtest, calibration, or study.
---

# Investment Research Workflow

Structured workflow for quantitative investment research. Guides projects from question → data → analysis → deliverable.

## When to Use

- Starting a new research topic (risk calibration, factor study, allocation optimization)
- Structuring a research directory
- Planning data sourcing and validation
- Building simulation/backtest pipelines
- Producing research deliverables (dashboards, reports, data files)
- Reviewing or extending existing research

## Research Lifecycle

Investment research follows a different pattern than ML research. There's no train/test split — instead there's **expert input → data validation → simulation → calibration → delivery**.

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐    ┌────────────┐
│  1. QUESTION │───>│  2. DATA      │───>│  3. ANALYSIS   │───>│  4. CALIBRATE│───>│  5. DELIVER │
│              │    │              │    │               │    │             │    │            │
│ What are we  │    │ Source, clean │    │ Simulate,     │    │ Expert input│    │ Dashboard, │
│ trying to    │    │ validate,    │    │ compute       │    │ + data =    │    │ JSON, report│
│ decide?      │    │ proxy        │    │ metrics       │    │ final params│    │            │
└─────────────┘    └──────────────┘    └───────────────┘    └─────────────┘    └────────────┘
       │                  │                    │                   │                   │
   question.md        data/raw/          scripts/*.py          config/           output/{run}/
                      data/processed/    scratch/              templates/        deliverable
```

## Quick Start: Initialize a Research Topic

When starting new research, create this structure:

```
research/{topic-name}/
├── README.md                    # What, why, status, how to run
├── data/
│   ├── raw/                     # Untouched source files (Excel, CSV, API dumps)
│   ├── intermediate/            # Cleaned/transformed (parquets, merged datasets)
│   └── processed/               # Final analysis-ready datasets
├── templates/                   # HTML templates, JSON schemas, report templates
├── output/                      # Timestamped run directories
│   └── {YYYYMMDD-HHMMSS}/      # Each run is immutable snapshot
├── archive/                     # Superseded scripts, old outputs
├── build_*.py                   # Pipeline scripts (numbered by dependency order)
└── scratch/                     # Temporary exploration (gitignored)
```

### README Template

Every research topic gets a README answering:

```markdown
# {Topic Name}

{One paragraph: what question this research answers and what it produces.}

## Pipeline

Run in order:
1. `uv run python build_data.py` — {what it does}
2. `uv run python simulate.py` — {what it does}
3. `uv run python build_output.py` — {what it does}

## Key Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}

## Status
- [x] Data sourced and validated
- [x] Simulation complete
- [ ] Calibration review with expert
- [ ] Dashboard delivered
```

## Phase 1: Question

Before writing any code, document the research question.

**Ask yourself:**
- What decision will this research inform?
- Who is the audience? (internal team, advisor, client)
- What is the deliverable? (dashboard, config file, report, data file)
- What are the expert's priors? (starting allocations, expected ranges, constraints)

**Capture in README.md** — not a separate document. Keep it living.

### Investment Research Question Types

| Type | Example | Typical Deliverable |
|------|---------|-------------------|
| **Allocation** | "What weights for 5 risk profiles?" | Config JSON + dashboard |
| **Risk** | "What's the worst-case for this portfolio?" | Stress test report |
| **Performance** | "How did strategy X perform?" | Performance dashboard |
| **Factor** | "Does momentum work in Polish equities?" | Factor study + backtest |
| **Instrument** | "Which ETFs best proxy our asset classes?" | Comparison table + recommendation |
| **Calibration** | "Are our risk parameters still valid?" | Updated parameters + evidence |

## Phase 2: Data

### Data Sourcing

Use the **market-datasets** skill for price/return data. For other sources:

```python
# Standard data pipeline script pattern
"""
Build {description}.

Sources:
- {Source 1}: {what it provides}
- {Source 2}: {what it provides}

Produces:
- data/processed/{output_file} — {description}
"""
```

### Data Validation Checklist

Before trusting any dataset:

- [ ] **Coverage**: Does the date range cover all needed periods (including crisis periods)?
- [ ] **Frequency**: Is it daily/monthly/quarterly as needed?
- [ ] **Completeness**: Missing values? Gaps in time series?
- [ ] **Proxy validation**: If using synthetic/proxy data, how does it compare to real data?
- [ ] **Dividend treatment**: Total return or price return? Adjusted or raw?
- [ ] **Currency**: Consistent currency? FX adjustments needed?
- [ ] **Survivorship bias**: Are delisted/merged instruments handled?

### Proxy Validation Pattern

When using long-history proxies (synthetic indices, academic datasets), validate against real data in the overlap period:

```python
# Compare proxy vs real in overlap window
overlap = proxy.merge(real, on='date', suffixes=('_proxy', '_real'))
print(f"Correlation: {overlap.corr()}")
print(f"Return diff: {(overlap.ret_proxy - overlap.ret_real).describe()}")
print(f"Vol ratio: {overlap.ret_proxy.std() / overlap.ret_real.std():.2f}")
```

Document the comparison in a `compare_*.py` script, then archive it once validated.

## Phase 3: Analysis

### Simulation Pattern

For portfolio/allocation research, the standard approach is:

1. **Sweep the parameter space** — don't guess, enumerate
2. **Compute risk metrics for every combination**
3. **Select from the feasible set** based on criteria + expert input

```python
# Typical simulation structure
results = []
for weights in weight_combinations:
    portfolio_returns = (returns * weights).sum(axis=1)
    metrics = compute_risk_metrics(portfolio_returns)
    results.append({**weights, **metrics})

results_df = pd.DataFrame(results)
results_df.to_parquet("data/processed/simulation_results.parquet")
```

### Standard Risk Metrics

Always compute this core set (extend as needed):

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Ann. Return | `(1+r).prod()^(12/n) - 1` | Compound annual growth |
| Ann. Volatility | `r.std() * sqrt(12)` | Annualized monthly std dev |
| Sharpe Ratio | `return / volatility` | Return per unit risk |
| Max Drawdown | `min(cumulative peak-to-trough)` | Worst peak-to-trough loss |
| Max DD Duration | `longest recovery time (months)` | Longest underwater period |
| Worst 12M | `min(rolling 12-month return)` | Worst rolling year |
| % Time DD > 5% | `pct of months below -5% from peak` | Pain frequency |
| Ulcer Index | `sqrt(mean(DD^2))` | RMS of drawdown (penalizes deep+long) |

### Crisis Period Analysis

Define named crisis windows and compute compound returns through each:

```python
CRISES = {
    "GFC 2007-09": ("2007-10", "2009-02"),
    "COVID 2020": ("2020-02", "2020-03"),
    "Rate Shock 2022": ("2022-01", "2022-09"),
    "Dot-com 2000-02": ("2000-03", "2002-09"),
}
```

Crisis returns validate **monotonic risk progression** — P1 should lose least, P5 most, in every crisis. Non-monotonicity signals a data or methodology problem (or a genuinely unusual regime like 2022 rate shock hitting bonds).

### Recency Analysis

Always compare full-period vs recent-period metrics. Forward-looking guidance should use recent period, while tail risk uses full period.

## Phase 4: Calibrate

This is where investment research diverges most from ML. Calibration is a **human-in-the-loop** process.

### Expert-Then-Data Pattern

```
Expert proposes starting parameters (SAA, bounds, constraints)
    ↓
Data validates/challenges expert proposals
    ↓
Adjustments documented with rationale
    ↓
Final parameters = expert + data evidence
```

### What to Calibrate

| Parameter | Expert Provides | Data Validates |
|-----------|----------------|----------------|
| Asset allocations | Starting weights per profile | Risk metrics, drawdowns at those weights |
| Tactical bounds | Min/max ranges per asset | Metrics at corridor edges stay in-character |
| Risk targets | "P1 should lose max 10%" | Actual max DD at proposed allocation |
| Constraints | "P1 has no equity" | Whether constraint impacts return meaningfully |

### Documenting Calibration Decisions

In the dashboard or README, always show:
- **What expert proposed** (starting point)
- **What data showed** (backtest results)
- **What changed** (adjustments with rationale)
- **What stayed** (confirmed proposals)

## Phase 5: Deliver

### Deliverable Types

| Type | When | How |
|------|------|-----|
| **Interactive dashboard** | Research presentation, stakeholder review | Use `investment-research-dashboard` skill |
| **Config JSON** | Parameters feeding production app | `templates/{name}.json` + timestamped copy |
| **Data file** | Input to another pipeline | `data/processed/{name}.parquet` |
| **Report** | Written analysis | Markdown or HTML |

### Timestamped Output Pattern

Every pipeline run produces an immutable snapshot:

```python
from datetime import datetime
from pathlib import Path

def make_run_dir(base: Path, manual: str | None = None) -> Path:
    d = Path(manual) if manual else base / datetime.now().strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    return d
```

All scripts accept `--output-dir` for manual override, defaulting to auto-timestamped. A pipeline run should target the same directory:

```bash
uv run python build_data.py                              # → output/20260306-150720/
uv run python build_dashboard.py --output-dir output/20260306-150720
```

### JSON Data Separation

Never hardcode analysis results in templates. Always:
1. **Python computes** → writes JSON
2. **Template consumes** → `const DATA = {};` placeholder
3. **Builder injects** → replaces placeholder with real data

This means templates are reusable across runs and the data is inspectable/diffable.

## Script Naming Convention

```
build_asset_data.py       # Phase 2: data sourcing & cleaning
compare_data_sources.py   # Phase 2: validation (archive after use)
simulate_profiles.py      # Phase 3: analysis/simulation
build_dashboard_data.py   # Phase 5: compute deliverable data
build_template_data.py    # Phase 5: compute app config data
build_dashboard_html.py   # Phase 5: assemble final deliverable
```

Prefix with `build_` for pipeline scripts. Use `compare_`, `validate_`, `explore_` for one-time analysis scripts (archive when done).

## Archiving

Research generates throwaway scripts. Archive aggressively:

**Archive when:**
- v1 script superseded by v2
- One-time validation complete
- Data comparison done and documented
- Old output snapshots replaced

**Keep active:**
- Current pipeline scripts
- Templates
- Processed data
- Latest output

## Guidelines

- **README is the source of truth** — not separate hypothesis/finding docs. Investment research is too iterative for formal hypothesis tracking.
- **Visual feedback over code review** — open the dashboard, spot issues with your eyes. Charts expose bugs that unit tests miss.
- **Subsample with care** — always preserve extremes (trough points, peak values) when reducing time series for charts.
- **Store ratios, display percentages** — JSON stores 0.057, charts show 5.7%. Avoids double-conversion bugs.
- **Expert input is data** — treat domain expert parameters as first-class inputs, not afterthoughts.
- **Archive, don't delete** — research is non-linear. You may need that "throwaway" script next quarter.

## Reference Implementation

`research/risk-profile-calibration/` is the canonical example of this workflow applied to SAA calibration across 5 risk profiles.

## Complementary Skills

| Skill | Use For |
|-------|---------|
| `market-datasets` | Sourcing price/return data |
| `investment-research-dashboard` | Building interactive HTML deliverables |
| `investment-research-formal` | Formalizing findings for compliance/audit |
| `analizy-pl-data` | Polish fund data from analizy.pl |
