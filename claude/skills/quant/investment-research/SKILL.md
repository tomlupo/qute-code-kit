---
name: investment-research
description: Guides quantitative investment research — both fresh studies and iterative methodology refinement on existing systems. Use when starting a new research topic, structuring a research directory, comparing methodology variants, re-testing hypotheses against updated baselines, deciding between competing approaches, promoting research findings to production, or working with backtest, calibration, and signal design. Covers the full lifecycle from data sourcing through analysis to deliverable, plus the iterative loop of explore → lock → re-test on already-deployed subsystems.
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

## Branch Lifecycle (Git mechanics)

Research branches are **per-question, short-lived**. Work flow:

```
1. START      git checkout -b research/{model}-{question-slug} dev
              mkdir research/{model}/experiments/{exp-id}/
              update research/{model}/README.md (status: in-progress)

2. ITERATE    add experiments + intermediate results (no merge yet)

3. CONCLUDE   write research/{model}/findings/{question-slug}.md
              update README.md status: concluded

4. MERGE      PR research/{model}-{slug} → dev
              findings + experiments + README land on dev; branch deleted

5. PROMOTE    (optional, only if findings warrant prod change)
              git checkout -b feat/{model}-{change} dev
              modify /src/, /pipelines/, /config/
              PR dev → main; /promote → tag prod-{model}-vX.Y.Z-YYYYMMDD
```

**One branch = one question.** New question = new branch. The `research/{model}/` directory on `dev` is the long-lived home; branches are ephemeral.

**A research branch modifies only `experiments/{exp-id}/`** — not the shared `scripts/` library, not `/src/`, not `/pipelines/`. Shared-methodology changes go on a separate `feat/*` branch (the promotion path).

**Status states** (declared in model `README.md` per question):
- `in-progress` — branch open, work ongoing
- `concluded` — findings.md written, branch ready to merge
- `merged` — findings on `dev`, branch closed
- `abandoned` — merged with findings.md = "tried, didn't work, here's why"
- `superseded` — findings replaced by later research

See `.claude/rules/research-workflow.md` and `.claude/rules/git-workflow.md` for the full conventions.

## Methodology Lifecycle

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

## Signal Research Lifecycle (8 stages)

For **signal-driven** research (TAA, factor models, fund scoring, sector rotation), the Analysis phase decomposes into 8 stages with one artifact each:

| # | Stage | Artifact |
|---|---|---|
| 1 | Signal generation | List of candidate raw signals + economic story per signal |
| 2 | Per-signal anatomy | Per-signal dashboard (distribution + history + crisis traces) |
| 3 | Per-signal IC | IC table per signal × horizon × era |
| 4 | Distribution & normalization | Per-component normalization spec |
| 5 | Ensemble construction | Variants v{N} in EXPERIMENTS.md, ONE change each |
| 6 | Weight engine | Weight engine spec + corridor sensitivity per profile |
| 7 | Portfolio backtest | Per-profile + per-regime + per-asset attribution table |
| 8 | Lock & promote | STATUS update, EXPERIMENTS lock entry, spec §, feat/ branch |

**MANDATORY for stage 7:** Use the `backtest` skill (vbt `run()`). Manual weighted-sum loops over monthly returns inflate IR by ~0.20 (empirically confirmed). See backtest skill Critical Rule #1.

**Stage 4 is a trap.** Normalization choice (per-asset rolling z vs bucket-pooled vs globally-pooled vs percentile rank vs tanh) materially changes which structural information survives — the default "z-score everything per-asset" reflex erases cross-asset structural premia (e.g. EM persistently cheap). Read the reference before designing your normalization layer.

**Stage 4 lookahead hazard.** Pooled normalization (bucket or global) MUST use walk-forward pool stats — at each eval_date T, μ/σ from data `≤ T` (rolling window or expanding). A full-panel pool is lookahead even when per-cat inputs are PIT. Observed cost: ~13% IR inflation on a real project. Rolling 10Y / 5Y-min matches the per-cat rolling_z convention and is ~20 lines. See reference §Stage 4 "Pool normalization MUST be walk-forward".

**Iteration discipline:** ONE change per variant. Don't layer "new normalization + new clip + new weights" into one variant — you can't attribute the result.

Full playbook (per-stage decisions, anti-patterns, dir mapping): see `references/signal-research-lifecycle.md`.

## Quick Start: Initialize a Research Topic

A model directory accretes findings + experiments across many questions. Create on first question's branch:

```
research/{model}/
├── README.md                    # Active + concluded questions index, status, prod state
├── EXPERIMENTS.md               # Append-only chronological log
├── findings/                    # Per-question findings (one .md per merged question)
│   └── {question-slug}.md       #   Written on conclusion; lands on dev via merge
├── experiments/                 # Per-experiment artifacts
│   └── {exp-id}/                #   Owned by one research branch — don't cross-modify
├── docs/                        # Methodology spec(s) with LOCKED frontmatter
├── data/
│   ├── raw/                     # Untouched source files (Excel, CSV, API dumps)
│   ├── intermediate/            # Cleaned/transformed (parquets, merged datasets)
│   └── processed/               # Final analysis-ready datasets
├── scripts/                     # Shared methodology library (modified only via feat/* branches)
├── templates/                   # HTML templates, JSON schemas, report templates
├── output/                      # Timestamped run directories
│   └── {YYYYMMDD-HHMMSS}/      # Each run is immutable snapshot
├── archive/                     # Superseded scripts, old outputs
└── scratch/                     # Temporary exploration (gitignored)
```

**On a research branch**, you only ADD to `experiments/{exp-id}/` and write `findings/{question-slug}.md` on conclusion. The README status update is the other branch-side change.

**On the first-ever question for a model**, the merge to `dev` also creates the `README.md`, `EXPERIMENTS.md`, and any of the directories above that the question populates.

### Mature-stage evolution: 4-track structure

Once a topic accumulates ~10+ build_*.py files **and** the work splits into distinct activities (per-signal EDA + variant experiments + portfolio backtests + methodology comparisons), promote the flat structure to four tracks:

```
research/{topic-name}/
├── validation/    ← per-signal EDA  (eq_*, fi_*, dcf, build_dashboard.py)
├── scoring/       ← composite/variant experiments  (backtest, ic_analysis, com_value_*)
├── backtesting/   ← portfolio P&L (drift-aware vbt)
├── comparison/    ← methodology diffs  (v3 vs v4 indicator dashboard)
├── docs/  config/  data/  scripts/
├── STATUS.md  EXPERIMENTS.md  README.md  CLAUDE.md
```

**Don't preemptively split.** Start flat. Split when the flat structure hurts — i.e., when one directory (commonly `validation/` or `analyses/`) starts hosting work that doesn't match its name. The 8-stage lifecycle above maps cleanly: stages 2 → validation/, 3-5 → scoring/, 7 → backtesting/, methodology-diff dashboards → comparison/.

### README Template

Every model README is a living index of questions + production state:

```markdown
# {Model Name}

{One paragraph: what this model is + what it produces in production.}

## Active questions

| Question | Branch | Status | Findings |
|---|---|---|---|
| Does decay improve regime detection? | `research/{model}-momentum-decay` | in-progress | (pending) |

## Concluded questions

| Question | Findings | Promoted? |
|---|---|---|
| Should ERP use DCF vs Damodaran T12m? | findings/erp-dcf-vs-damodaran.md | yes — `prod-{model}-v4.0.0-20260408` |

## Production state

Latest tag: `git tag --list 'prod-{model}-*' | sort -V | tail -1`.
Methodology spec: `docs/signal-definitions-v{N}.md` (latest LOCKED version per the file's frontmatter `version` field).

## Pipeline

Run in order:
1. `uv run python build_data.py` — {what it does}
2. `uv run python simulate.py` — {what it does}
3. `uv run python build_output.py` — {what it does}

## Key Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}
```

The README is the model's living index. Adding a question = new row in Active. Concluding = move to Concluded with findings link. Promoting = note prod tag.

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

**For portfolio backtests, MANDATORY:** use the `backtest` skill. Do NOT roll your own monthly weighted-sum loop — manual loops skip intra-period weight drift and produce optimistically biased Sharpe/IR (empirically observed: +0.20 avg IR inflation on a 10-year monthly-rebalanced study, see backtest skill Critical Rule #1).

```python
# Cross-sectional metric sweep (no time-series rebalance — fine for static metrics)
results = []
for weights in weight_combinations:
    portfolio_returns = (returns * weights).sum(axis=1)
    metrics = compute_risk_metrics(portfolio_returns)
    results.append({**weights, **metrics})

# Time-series portfolio backtest (use backtest skill, NOT the loop above):
from src.vectorbt_tools.backtesting import run as vbt_run
pf = vbt_run(prices, {"Strategy": w_df, "Benchmark": w_bench_df},
             rebalancing_freq="1M", fees=0.001)
# pf.stats(), pf.drawdowns.records_readable, etc. — see backtest skill
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

`research/strategic-asset-allocation/` is the canonical example of this workflow applied to SAA calibration across 5 risk profiles.

## Complementary Skills

| Skill | Use For |
|-------|---------|
| `market-datasets` | Sourcing price/return data |
| `backtest` | **MANDATORY for any portfolio-level backtest** — vbt-based weight-driven simulation with drift, fees, multi-strategy comparison. Manual weighted-sum loops produce optimistically biased Sharpe/IR (~0.20 inflation observed). |
| `investment-research-dashboard` | Building interactive HTML deliverables |
| `investment-research-formal` | Formalizing findings for compliance/audit |
| `analizy-pl-data` | Polish fund data from analizy.pl |
| `evo-dm-brand` | Applying brand identity to dashboards |
