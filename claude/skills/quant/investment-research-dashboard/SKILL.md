---
name: investment-research-dashboard
description: Builds self-contained HTML dashboards for investment and finance research using Plotly.js. Use when building interactive dashboards, research reports, or data visualizations for portfolio analysis, risk metrics, fund performance, asset allocation, drawdowns, or any quantitative finance presentation. Produces single-file HTML with embedded data — no server needed, shareable, works offline.
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

See [references/css-components.md](references/css-components.md) for complete CSS.

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

Use these chart types for the corresponding data. See [references/chart-patterns.md](references/chart-patterns.md) for full code.

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

**With brand skill**: Invoke alongside a project-specific brand skill to override CSS variables:

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

See `research/risk-profile-calibration/` for the canonical example:
- `templates/exec_summary_template.html` — full dashboard template
- `build_dashboard_data.py` — Python data builder
- `build_dashboard_html.py` — HTML builder with JSON injection

## Detailed References

- [CSS Components](references/css-components.md) — Complete CSS for all component classes
- [Chart Patterns](references/chart-patterns.md) — Full Plotly.js code for each chart type
