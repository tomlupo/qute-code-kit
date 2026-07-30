---
name: investment-research-dashboard
description: Builds self-contained HTML dashboards for investment and finance research using Plotly.js. Use when building interactive dashboards, research reports, or data visualizations for portfolio analysis, risk metrics, fund performance, asset allocation, drawdowns, or any quantitative finance presentation. Produces single-file HTML with embedded data — no server needed, shareable, works offline.
allowed-tools: Write, Bash, Read, Edit, Glob, Grep
---

# Investment Research Dashboard

Build professional, self-contained HTML dashboards for quantitative finance research. Single HTML file output with embedded JSON data and Plotly.js charts — no build step, no server, fully shareable.

## When to Use

- Portfolio analysis dashboards (risk profiles, allocations, performance)
- Fund/strategy performance reports (returns, drawdowns, benchmarks)
- Risk metric visualizations (VaR, drawdowns, stress tests, correlations)
- Asset allocation studies (efficient frontier, rebalancing analysis)
- Any quantitative finance presentation needing interactive charts

## Quick Start

A dashboard has two parts: **Python data builder** and **HTML template**.

### 1. Python Data Builder

Computes all metrics and writes a JSON file:

```python
import json
from pathlib import Path
from datetime import datetime

def make_run_dir(base: Path, manual_override: str | None = None) -> Path:
    if manual_override:
        d = Path(manual_override)
    else:
        d = base / datetime.now().strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    return d

def build_data() -> dict:
    """Build all dashboard data. Return a single dict."""
    return {
        "metadata": {"title": "...", "generated": "...", "period": "..."},
        "profiles": { ... },    # per-entity data
        "summary": { ... },     # aggregate metrics
        # ... domain-specific sections
    }

data = build_data()
run_dir = make_run_dir(Path("output"))
(run_dir / "dashboard_data.json").write_text(
    json.dumps(data, separators=(",", ":")), encoding="utf-8"
)
```

### 2. HTML Template

Self-contained file with a `DATA` placeholder:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Title</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>/* CSS here */</style>
</head>
<body>
<!-- HTML structure -->
<script>
const DATA = {};
/* Chart rendering code */
</script>
</body>
</html>
```

### 3. HTML Builder

Injects JSON into the template:

```python
DATA_PLACEHOLDER = "const DATA = {};"
template = Path("templates/dashboard_template.html").read_text(encoding="utf-8")
data_str = json.dumps(data, separators=(",", ":"))
html = template.replace(DATA_PLACEHOLDER, f"const DATA = {data_str};")
Path(run_dir / "dashboard.html").write_text(html, encoding="utf-8")
```

## Architecture

```
project/
  templates/
    dashboard_template.html    # HTML + CSS + JS with DATA placeholder
  build_data.py                # Python: compute metrics → JSON
  build_html.py                # Python: inject JSON → self-contained HTML
  output/
    {YYYYMMDD-HHMMSS}/         # Timestamped run output
      dashboard_data.json
      dashboard.html           # Final deliverable
```

**Key principle**: Template never changes between runs. All variable content comes from JSON data. The template is pure presentation logic.

### When to Split vs Single-File

| Approach | When to use | Trade-off |
|----------|-------------|-----------|
| **Split** (separate template + data builder) | Production dashboards rebuilt regularly with new data. >500 lines of HTML. Team collaboration on styling. | Template editable in HTML editor, data builder testable independently. |
| **Single-file** (HTML in Python string) | Research/exploration dashboards that change frequently. <500 lines HTML. Fast iteration during development. | Faster iteration, no file juggling, but harder to maintain long-term. |

For single-file approach, use `HTML.replace("__DATA_JSON__", json.dumps(data))` pattern. For split approach, use `const DATA = {};` placeholder in the template file.

### Hard split rule (enforced)

The trade-off above describes the choice during initial implementation. Once a
dashboard crosses the thresholds below, **the split is mandatory**, not
optional — single-file mode is for exploration, not for production-grade
dashboards that get rebuilt and reviewed by collaborators.

**Trigger conditions** (any one is sufficient):

- Python builder file > 500 lines (`wc -l build_dashboard.py`)
- Inlined HTML/CSS/JS string > 500 lines (length of the triple-quoted block)
- Dashboard is rebuilt by an automated pipeline (cron, CI, scheduled report)
- Two or more people (incl. future-you and an AI agent) will edit the file

**Required architecture once triggered:**

```
{pipeline_dir}/
├── build_dashboard.py          # thin orchestrator (≤100 lines): args, run_dir, calls into dashboard.{data,html}
├── dashboard/
│   ├── __init__.py
│   ├── data.py                 # build_data(...) -> dict; pure compute, no HTML
│   ├── html.py                 # render_html(data, template_path) -> str; inject + write
│   └── charts.py               # (optional) Plotly trace builders, shared layout helpers
└── templates/
    └── dashboard.html          # template with `const DATA = {};` placeholder; no Python here
```

**Each module has one job:**

| File | Responsibility | Forbidden content |
|---|---|---|
| `build_dashboard.py` | Orchestration only — argparse, run_dir, calls into `dashboard.data` and `dashboard.html` | Metric computation, HTML strings, chart code |
| `dashboard/data.py` | Compute every number/series the template needs; emit a single nested dict | HTML, CSS, JS, Plotly JSON, file I/O of HTML |
| `dashboard/html.py` | Read template, inject `const DATA = {...};`, write final `.html` | Metric computation, dataframe slicing |
| `dashboard/charts.py` (optional) | Plotly trace + layout helpers, shared across panels | Domain logic, file I/O |
| `templates/dashboard.html` | All HTML, CSS, JS, Plotly rendering; reads `const DATA` only | Python, dynamic file paths, inline data values |

**Pre-merge compliance checklist** — run before any PR that adds or touches a dashboard:

- [ ] `wc -l build_dashboard.py` ≤ 100 (orchestrator stays thin)
- [ ] `dashboard/` package exists with at minimum `data.py` and `html.py`
- [ ] `templates/*.html` exists; the `.html` is the only place `<style>`, `<script>`, or Plotly chart code lives
- [ ] `grep -c "<html\|<style\|plotly" build_dashboard.py dashboard/*.py` returns `0` for each file
- [ ] `grep -c "const DATA" templates/*.html` returns `1` per template; same grep on `dashboard/*.py` returns `0`
- [ ] `data.py` has a single public entry point (`build_data(...) -> dict`) and no HTML imports

If any check fails, the dashboard does not ship — refactor to the split layout
first. The thresholds aren't aesthetic preference; they're a debt-prevention
forcing-function. The two existing TAA dashboards in this repo
(`pipelines/tactical_signals/build_dashboard.py` at 1585 lines and
`research/tactical-signals/validation/build_dashboard.py` at 1423 lines, both
with inlined HTML/CSS/JS, neither with a `templates/` dir) demonstrate the
failure mode the rule prevents — every metric tweak now requires editing
1500+ lines of mixed Python+HTML, and a styling change can't be made without
a Python developer.

## Dashboard Layout

Use this standard layout structure. Adapt sections to your domain.

```
┌─────────────────────────────────────┐
│  HEADER (dark bg, title, subtitle)  │
├─────────────────────────────────────┤
│  NAV (sticky, section links)        │
├─────────────────────────────────────┤
│  SECTION 1: Methodology             │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │ KPI │ │ KPI │ │ KPI │ │ KPI │  │
│  └─────┘ └─────┘ └─────┘ └─────┘  │
│  ┌────────────┐ ┌────────────┐     │
│  │ Chart/Table│ │ Chart/Table│     │
│  └────────────┘ └────────────┘     │
├─────────────────────────────────────┤
│  SECTION 2: Key Metrics             │
│  ┌─────────────────────────────┐   │
│  │ Full-width comparison table │   │
│  └─────────────────────────────┘   │
├─────────────────────────────────────┤
│  SECTION N: ...                     │
├─────────────────────────────────────┤
│  FOOTER                            │
└─────────────────────────────────────┘
```

### CSS Component Classes

```css
.header        — Dark primary background, white text, 48px padding
.nav           — Sticky top, horizontal scroll, tab-style links
.container     — max-width: 1200px, centered
.section       — 48px top padding, bottom border separator
.section h2    — Section title (primary color)
.section-desc  — Muted description text below title
.kpi-row       — Flex row of KPI cards
.kpi           — Individual metric card (value + label)
.chart-row     — Flex row for side-by-side charts
.chart-box     — Rounded card for chart content
.chart-box.full — Full-width chart card
.metrics-table — Styled data table with hover
.insight-box   — Callout box (accent border-left)
.chip          — Pill-shaped label/tag
.footer        — Light background, centered small text
```

When writing CSS, read `references/css-components.md` for the complete component library.

## Plotly.js Chart Patterns

### Shared Configuration

Always use these base settings for consistent styling:

```javascript
const LAYOUT_BASE = {
  font: { family: "-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif", size: 12 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  margin: { l: 50, r: 20, t: 30, b: 40 },
};
const CONFIG = { responsive: true, displayModeBar: false };

function pct(v, d=1) { return (v * 100).toFixed(d) + '%'; }
```

### Finance Chart Catalog

Use these chart types for the corresponding data. When implementing charts, read `references/chart-patterns.md` for full copy-paste code patterns.

| Chart Type | Use For | Key Options |
|------------|---------|-------------|
| **Stacked bar** | Allocations, compositions | `barmode:'stack'`, textPosition inside |
| **Grouped bar** | Cross-entity comparison | `barmode:'group'`, textPosition outside |
| **Time series** | Returns, prices, drawdowns | `mode:'lines'`, gridColor |
| **Drawdown** | Underwater chart | Negative y-axis, `fill:'tozeroy'` on worst, crisis `shapes` |
| **Cumulative growth** | Growth of $1 | `yaxis.type:'log'`, `tickprefix:'$'` |
| **Scatter** | Risk-return landscape | Color by 3rd metric, `colorbar`, diamond markers for selected |
| **Heatmap** | Correlation matrix | Custom `colorscale`, `texttemplate:'%{text}'` |
| **Bullet/range** | Bounds, corridors | Bar for range + scatter markers for point values |
| **Radar/spider** | Multi-metric comparison | `type:'scatterpolar'`, normalized scales |
| **HTML gradient table** | Metric comparison | JS-built table with `lerpColor()` backgrounds |
| **Crisis comparison bars** | Strategy vs benchmark per crisis | `barmode:'group'`, protection delta, zero-line |
| **Conditional performance** | Up/down market excess returns | Sign-colored bars, market regime split |
| **Signal heatmap** | Time × category scores | Diverging colorscale, symmetric `zmin/zmax` |
| **Regime timeline** | Multi-entity state over time | Multiple lines with threshold dashed bands |
| **Signal anatomy** | Quant signal construction (L0 inputs → z-score → clipped signal) | Multi-panel top-to-bottom decomposition. See `references/signal-construction-pattern.md` |
| **Z-score histogram** | Calibration check for rolling z | Explicit linear axes + ±1.5σ clip lines + zero line |
| **Decomposition overlay** | Combined signal with components | Solid main trace + dotted/faded component traces at `opacity: 0.6` |
| **Expanding-window shading** | Flag periods where signal quality is weaker | `type: 'rect', yref: 'paper'` rectangle with low-alpha fill + small annotation |

### Mandatory Plotly Rules

**Categorical axes**: When using string labels (names, profiles, categories) on any axis, always set `type: 'category'` in the axis config. Plotly auto-detection frequently misinterprets strings as dates, rendering timestamps (e.g., "Jan 1970") instead of labels. See chart-patterns.md gotcha #7 for details.

**Histogram axes**: Explicitly set `xaxis.type: 'linear'` AND `yaxis.type: 'linear'` on histogram charts. Plotly can misdetect numeric bin data as dates when the values are passed as floats from JSON, producing garbage tick labels. Pair with explicit `xbins: {start, end, size}` and `xaxis.range: [start, end]` to lock the display.

**Two-axis overlays**: When overlaying two series on different scales (e.g. price + return, price + earnings-yield), the secondary axis needs `gridcolor: 'rgba(0,0,0,0)'` to suppress duplicate grid lines. Use `overlaying: 'y'`, `side: 'right'`, and add a `title.standoff` to keep tick labels legible. Example:

```javascript
yaxis:  { gridcolor: '#E5E7EB', title: { text: 'P (level)', standoff: 8 } },
yaxis2: { overlaying: 'y', side: 'right', gridcolor: 'rgba(0,0,0,0)',
          zeroline: true, zerolinecolor: '#CBD5E1',
          title: { text: 'return', standoff: 8 }, ticksuffix: '%' },
```

### KPI Guidance

KPIs occupy the most prominent slot in the dashboard and set the reader's mental model. Choose them deliberately.

1. **KPIs are your output, not your references.** External benchmarks (e.g. Damodaran ERP, index levels, peer funds) belong in validation panels or the decomposition section — not in the top KPI row. If you're tempted to put "Damodaran current" and "our current" side-by-side as KPIs, the comparison belongs in a chart with the reference series faded, not in two KPI cards.

2. **Always include the "money KPI"** — the single number that IS the decision input downstream. For a tactical signal, it's the combined clipped signal. For a portfolio, it's the suggested weight delta. Mark it visually (tone gating or star) so the reader knows where to look first.

3. **Always include an "operational confidence" KPI** — something that answers "can I trust this right now?" Examples: data freshness (days since last input), pipeline-success rate, calibration health (% of distribution at clip). Without this, readers assume the signal is always fresh, which it rarely is.

4. **Tone gating needs documented thresholds.** Green/amber/red cards only help when the bands are explicit:
   ```
   freshness  ≤ 14d   → good
             15–40d   → warn
              > 40d   → bad
   ```
   Keep thresholds in constants next to the KPI render code, not magic numbers.

5. **Six is the sweet spot.** Fewer than 4 wastes the row; more than 8 overwhelms. Prefer 5–6 cards with decomposition charts handling the detail.

### Insight Boxes

Place `.insight-box` elements after charts that show **counterintuitive or surprising findings**. Do not explain obvious charts.

Structure:
1. **Bold key takeaway** — one sentence stating the finding
2. Explanation of the mechanism — why this happens
3. Implication for the user's decision — what to do about it

Example: After a chart showing "bear regime has highest forward returns," the insight box explains this is the mean-reversion effect (signals lag), confirms it's by design (risk identification, not return prediction), and frames the cost as insurance premium.

### Formatting Conventions

```javascript
// Percentages: store as ratios in JSON, multiply by 100 for display
y: data.values.map(v => v * 100)
ticksuffix: '%'

// Currency
tickprefix: '$'

// Hover templates — always include <extra></extra> to hide trace name box
hovertemplate: 'P1: %{y:.1f}%<extra></extra>'

// Legend — horizontal, centered above chart
legend: { orientation: 'h', y: 1.12, x: 0.5, xanchor: 'center' }

// Grid lines — light gray
gridcolor: '#E5E7EB'

// Zero line emphasis (for drawdown/return charts)
zeroline: true, zerolinecolor: '#CBD5E1', zerolinewidth: 2
```

### Color Palettes

**Entity colors** (for profiles, strategies, funds — up to 5):
```javascript
const COLORS = {
  entity1: '#2563EB',  // blue
  entity2: '#0284C7',  // sky
  entity3: '#059669',  // emerald
  entity4: '#D97706',  // amber
  entity5: '#DC2626',  // red
};
```

**Asset class colors** (for allocation charts):
```javascript
const ASSET_COLORS = {
  cash:        '#94A3B8',  // slate
  fixed_income:'#2563EB',  // blue
  equity:      '#059669',  // green
  alternatives:'#D97706',  // amber
  crypto:      '#8B5CF6',  // violet
};
```

**Gradient table** (best → mid → worst):
```javascript
// Blue (best) → Amber (mid) → Red (worst)
[[0, [219,234,254]], [0.5, [254,243,199]], [1, [254,226,226]]]
```

## Data Flow Conventions

### JSON Structure

```javascript
{
  "metadata": {
    "title": "Dashboard Title",
    "generated": "2026-03-06",
    "period": "1968-2025",
    "n_months": 695
  },
  "profiles": {               // or "funds", "strategies" — the main entities
    "P1": {
      "weights": { ... },      // allocations
      "full": { ... },         // full-period metrics
      "recent": { ... },       // sub-period metrics
      "dd_dates": [...],       // time series (subsampled)
      "dd_values": [...],      // as ratios, not percentages
      "cum_dates": [...],
      "cum_values": [...]
    }
  },
  "asset_stats": { ... },     // per-asset summary
  "correlation": { ... },     // correlation matrix
  "crises": [ ... ],          // crisis period returns
  "sim_scatter": { ... }      // scatter plot data
}
```

### Important: Ratio vs Percentage Convention

- **JSON**: Store all percentage values as **ratios** (0.057 not 5.7)
- **Display**: Multiply by 100 in JavaScript (`v * 100`)
- **Why**: Avoids double-conversion bugs, consistent with pandas/numpy output

### Time Series Subsampling

For long time series (>500 points), subsample to ~200 points but **preserve extremes**:

```python
step = max(1, len(series) // 200)
sub = series.iloc[::step]

# Preserve the actual trough/peak
extreme_idx = series.idxmin()  # or idxmax()
if extreme_idx not in sub.index:
    sub = pd.concat([sub, series.loc[[extreme_idx]]]).sort_index()
```

## Brand Integration

This skill provides **layout, charts, and data patterns**. Visual identity (colors, fonts, logo) comes from a brand skill.

**Default**: Uses professional finance defaults (navy/blue/white theme). Works well standalone.

**With brand skill**: Invoke alongside a brand skill (e.g., `evo-dm-brand`) to override CSS variables:

```css
:root {
  --primary: #0C2340;      /* Override with brand primary */
  --accent: #2563EB;       /* Override with brand accent */
  --bg: #FFFFFF;           /* Override with brand background */
  /* ... */
}
```

The CSS variable system means brand changes propagate automatically — no need to modify chart code or layout.

## Guidelines

- **Single file output**: The final HTML must be fully self-contained (only external dependency: Plotly.js CDN)
- **No framework**: Pure HTML/CSS/JS. No React, no build step, no npm
- **Responsive**: Use CSS flex/grid with media queries for mobile
- **Sticky nav**: Always include for dashboards with 3+ sections
- **Insight boxes**: Add after complex sections to highlight key takeaways
- **Table + chart**: Pair every comparison table with a visual chart
- **Footer**: Include data period, generation date, methodology note
- **Accessible**: Use semantic HTML, sufficient color contrast, tabular-nums for numbers

## Reference Implementation

See `research/strategic-asset-allocation/` for the canonical example:
- `templates/exec_summary_template.html` — full dashboard template
- `build_dashboard_data.py` — Python data builder
- `build_dashboard_html.py` — HTML builder with JSON injection

## Detailed References

**Do not read these upfront.** Read on-demand when you need the specific content:

- `references/css-components.md` — Read when writing dashboard CSS (complete component library with variables, layout classes, responsive breakpoints)
- `references/chart-patterns.md` — Read when implementing Plotly.js charts (copy-paste code for all 14 chart types + gotchas)
- `references/signal-construction-pattern.md` — Read when building dashboards for quant signal research (value/trend/z-score/clip anatomy, decomposition layout, validation separation, data-quality shading, typo rejection overlays)
