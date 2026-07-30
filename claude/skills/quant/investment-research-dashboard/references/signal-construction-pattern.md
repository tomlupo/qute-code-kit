# Signal Construction Dashboard Pattern

Specialized layout for quantitative signal research (value/trend/z-score/clip
chains). Use this pattern when the dashboard's job is to pressure-test how a
signal is built from raw inputs to final tilt, before taking it to production.

---

## When to use

Use this pattern when **all** of the following apply:
- The dashboard visualizes a single signal construction (or a small set of
  parallel signals) rather than a portfolio or a cross-section.
- Readers need to audit the full transformation chain: raw input → derived
  indicator → rolling z-score → clipped signal → combined output.
- There is at least one authoritative external reference you want to validate
  against, but the reference is not the story — your signal is.

Do NOT use this pattern when:
- The dashboard is a performance/allocation report — use the standard layout.
- You're showing a single time series without decomposition — a simple
  time-series chart is enough.

---

## Anatomy layout — top to bottom

The reader's eye moves top-to-bottom, so order reflects the narrative:

```
1. KPI row              ← "what's the signal saying NOW"
2. L0 inputs            ← raw market data (P, E, rf, g, CPI, …)
3. Derived indicator    ← the domain quantity (ERP, real yield, OAS, …)
4. Rolling mean (μ)     ← what the z-score centres on, with expanding-window shading
5. Z-score              ← with ±1.5σ clip lines
6. Clipped signal       ← the actual tilt input in [-1, +1]
7. Trend component      ← price + MOM inputs + trend z + trend signal
8. Combined signal      ← the money chart, with value-only + trend-only overlay
9. Distributions        ← value z + trend z histograms side-by-side
10. Validation panel    ← comparison vs external reference, AT THE BOTTOM
```

The **validation panel goes at the bottom**, not the top. Front-and-center
is reserved for the reader's own signal. An external reference appears only
as a sanity check — one chart, one line, explicitly labelled "validation only".

---

## Sub-pattern: L0 input decomposition

Before showing the signal, show what goes INTO it. For a DCF-implied ERP:

```
Chart row: [ P + E (two-axis) ]  [ EY + rf (shared % axis) ]
```

Two-axis overlay is the right tool when two series have different scales
(index level ~6500 vs cashflow ~200). Remember to suppress the secondary
grid: `yaxis2.gridcolor: 'rgba(0,0,0,0)'`.

This decomposition makes it obvious WHICH input moved when the signal changes.
PMs tracking "why did ERP drop 30 bp yesterday?" can read the answer off the
L0 panel (P rallied 5%, rf unchanged → EY down → ERP down).

---

## Sub-pattern: Expanding-window shading

When a rolling statistic uses an expanding→rolling window (e.g. 10Y capped,
min 5Y), the early period has weaker signal quality. Shade it.

```javascript
function expandShape(series_start, full_window_start) {
  return {
    type: 'rect', xref: 'x', yref: 'paper',
    x0: series_start, x1: full_window_start,
    y0: 0, y1: 1,
    fillcolor: 'rgba(148,163,184,0.18)', line: { width: 0 },
    layer: 'below',
  };
}
function expandAnnotation(series_start, full_window_start) {
  return {
    xref: 'x', yref: 'paper',
    x: series_start, y: 0.97, xanchor: 'left',
    text: 'expanding 5→10Y window', showarrow: false,
    font: { size: 9, color: '#64748B' },
  };
}
```

Apply the same shading+annotation to every time-series chart that inherits
the underlying window (level, z-score, signal, combined). Reader immediately
sees where the signal is trustworthy vs warming up.

---

## Sub-pattern: Decomposition overlay on combined signal

The combined signal chart should show the aggregate AS THE PRIMARY trace,
with component traces as dotted/faded overlays:

```javascript
[
  { x: combined.dates, y: combined.values, mode: 'lines', name: 'combined',
    line: { color: '#2563EB', width: 1.5 } },
  { x: value.dates, y: value.values, mode: 'lines', name: 'value only',
    line: { color: '#059669', width: 1, dash: 'dot' }, opacity: 0.6 },
  { x: trend.dates, y: trend.values, mode: 'lines', name: 'trend only',
    line: { color: '#D97706', width: 1, dash: 'dot' }, opacity: 0.6 },
]
```

Dotted + 60% opacity keeps the main trace dominant while letting the reader
attribute moves. "Combined bearish because value is bearish and trend is
flat" is readable at a glance.

---

## Sub-pattern: Z-score histogram as calibration check

Every rolling z-score should be accompanied by a histogram of its full-
history values, with the ±1.5σ clip lines overlaid. Pair value z and trend
z side-by-side in a final row:

```javascript
const histXBins = { start: -4, end: 4, size: 0.25 };
const histShapes = [
  { type: 'line', x0: 1.5, x1: 1.5, yref: 'paper', y0: 0, y1: 1,
    line: { color: '#DC2626', dash: 'dot', width: 1 } },
  { type: 'line', x0: -1.5, x1: -1.5, yref: 'paper', y0: 0, y1: 1,
    line: { color: '#DC2626', dash: 'dot', width: 1 } },
  { type: 'line', x0: 0, x1: 0, yref: 'paper', y0: 0, y1: 1,
    line: { color: '#94A3B8', width: 1 } },
];
const histLayout = {
  ...LAYOUT_BASE,
  xaxis: { gridcolor: '#E5E7EB', zeroline: false,
           type: 'linear',                        // CRITICAL — see gotcha
           range: [-4, 4], title: { text: 'z-score', standoff: 8 } },
  yaxis: { gridcolor: '#E5E7EB', zeroline: true, zerolinecolor: '#CBD5E1',
           type: 'linear',
           title: { text: 'observations', standoff: 8 } },
  bargap: 0.05,
  shapes: histShapes,
};
```

**Gotcha**: always set `xaxis.type: 'linear'` AND `yaxis.type: 'linear'` on
histograms. Plotly sometimes mis-detects float bins as dates and renders
"Jan 1970" labels. Explicit bin range + size locks the display.

Sanity-check reading:
- Distribution should be roughly normal-ish around zero.
- Fat tails past ±1.5σ → frequent pinning (clip fires often).
- Skew (median ≠ 0) → the rolling mean is trending below/above current level
  consistently, which usually reflects a post-crisis mean-reversion regime.

---

## Sub-pattern: Input-validation overlay (typo rejection)

Real-world financial data feeds have typos. When we detect and correct an
outlier, show BOTH the raw and the validated series:

```javascript
[
  { x: g_raw.dates, y: g_raw.values, mode: 'lines', name: 'g (raw)',
    line: { color: '#94A3B8', width: 1, dash: 'dot' } },
  { x: g_used.dates, y: g_used.values, mode: 'lines', name: 'g (validated)',
    line: { color: '#0C2340', width: 1.4 } },
]
```

Also surface the count of flagged observations in stats — when it starts
climbing, the upstream feed may have degraded. A silent fix is worse than
a visible fix.

Simple typo-rejection rule: flag `g[t]` as a typo only when it deviates from
BOTH neighbors by a meaningful threshold IN THE SAME DIRECTION. Catches
isolated single-month outliers without false-flagging regime transitions
(where values monotonically drift over several observations).

```python
for i in range(1, len(g_raw) - 1):
    d_prev = g_raw.iloc[i] - g_raw.iloc[i-1]
    d_next = g_raw.iloc[i] - g_raw.iloc[i+1]
    if d_prev * d_next > 0 and abs(d_prev) > THRESHOLD and abs(d_next) > THRESHOLD:
        g_validated.iloc[i] = (g_raw.iloc[i-1] + g_raw.iloc[i+1]) / 2
```

---

## Sub-pattern: Annual→daily interpolation

When inputs are published annually/monthly but the signal runs daily,
interpolate linearly between publication anchors rather than using a
step-function forward-fill. Prevents spurious jumps at year-turns.

```python
# Anchor annual values at Dec 31 of each year
annual_series.index = pd.to_datetime(annual_series.index.astype(str) + "-12-31")
# Daily reindex + linear interpolate + ffill past last anchor
daily = (
    annual_series.reindex(daily_idx)
    .interpolate(method="linear")
    .ffill().bfill()
)
```

For time-series display this is conceptually defensible: the underlying
fundamental drifts continuously, we just receive snapshot observations
periodically. Without it, the dashboard shows step jumps on every publication
anniversary that confuse readers into thinking the signal itself jumped.

**Exception**: if strict point-in-time replication is required (for backtest
honesty), use stepwise forward-fill instead and show the jumps explicitly.

---

## Sub-pattern: PIT availability lag

External data doesn't arrive instantly. If a source publishes "Start of
month 2026-04-01" data but it's not available until April 7, don't let
your DCF use it before it would have existed.

```python
DAMODARAN_LAG_DAYS = 7        # PIT: monthly obs published 1-7d after observation date
lag = pd.Timedelta(days=DAMODARAN_LAG_DAYS)
g_available = g.copy()
g_available.index = g_available.index + lag  # shift obs index forward
```

Make the lag a named constant near the top of the module, not buried in data
loading. This is load-bearing for backtest honesty, should be reviewable at a
glance. For dashboards, you can also expose `freshness = today − latest_available`
as an operational-confidence KPI with green/amber/red tone gating.

---

## KPI row composition for signal dashboards

Six is the sweet spot. Choose from this template:

| Slot | Purpose | Example |
|---|---|---|
| 1 | Current level of derived indicator | "ERP (current)" — 4.38% |
| 2 | Value component state | "Value z-score" — −0.67σ |
| 3 | Trend component state | "Trend z-score" — −0.33σ |
| 4 | **Money KPI** — final tilt | "**Combined signal**" — −0.33 |
| 5 | Calibration health | "Value pinned @ ±1.5σ" — 22% |
| 6 | Operational confidence | "Input freshness" — 13d |

Tone gating (documented thresholds):
- Freshness: `≤14d` green, `15-40d` amber, `>40d` red.
- Combined signal: `|v| < 0.2` neutral, otherwise coloured by direction.
- Pinned rate: `≤15%` green, `15-25%` amber, `>25%` red (calibration warning).

---

## Validation panel — explicit labelling

When including comparison vs external reference, label it clearly as
validation, not as a primary signal:

```html
<div class="chart-row full">
  <div class="chart">
    <h3>Validation — our daily DCF vs Damodaran T12m monthly</h3>
    <div class="ann">Sanity check for signal construction. ...</div>
    <div class="plot dcf"></div>
  </div>
</div>
```

Place as the LAST section (after distributions). Single chart, not a row of
comparisons. The tone in the subtitle/annotation should be "check that we're
tracking" — not "compare who is right."

If your reference publishes both daily and monthly, use one cadence only.
Daily markers + daily reference line is cleaner than mixing cadences on one
panel.
