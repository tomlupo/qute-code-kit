# Plotly.js Chart Patterns for Finance Dashboards

Complete code patterns for each chart type. Copy and adapt.

## Shared Setup

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

## 1. Stacked Bar — Allocation Composition

Shows how entities (profiles, funds) allocate across asset classes.

```javascript
const entities = ['P1', 'P2', 'P3', 'P4', 'P5'];
const assets = ['FI_SHORT', 'FI_AGG', 'Equity', 'Commodities'];

const traces = assets.map(a => ({
  x: entities.map(e => e + ' ' + NAMES[e]),
  y: entities.map(e => DATA.profiles[e].weights[a] * 100),
  name: a, type: 'bar',
  marker: { color: ASSET_COLORS[a] },
  text: entities.map(e => {
    const v = DATA.profiles[e].weights[a] * 100;
    return v > 0 ? v + '%' : '';
  }),
  textposition: 'inside',
  textfont: { color: 'white', size: 11 },
  hovertemplate: '%{x}: %{y:.0f}%<extra>' + a + '</extra>',
}));

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'stack', height: 250,
  yaxis: { title: 'Weight %', range: [0, 105] },
  legend: { orientation: 'h', y: 1.15, x: 0.5, xanchor: 'center' },
}, CONFIG);
```

## 2. Grouped Bar — Cross-Entity Comparison

Compares a metric across entities and categories (e.g., crisis returns per profile).

```javascript
const traces = entities.map(e => ({
  x: DATA.crises.map(c => c.name),
  y: DATA.crises.map(c => c[e]),
  name: e, type: 'bar',
  marker: { color: COLORS[e] },
  text: DATA.crises.map(c => c[e].toFixed(1) + '%'),
  textposition: 'outside',
  textfont: { size: 9 },
  hovertemplate: e + ': %{y:.1f}%<extra></extra>',
}));

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'group', height: 380,
  yaxis: {
    title: 'Total Return (%)', gridcolor: '#E5E7EB',
    ticksuffix: '%', zeroline: true,
    zerolinecolor: '#CBD5E1', zerolinewidth: 2,
  },
  legend: { orientation: 'h', y: 1.12, x: 0.5, xanchor: 'center' },
  margin: { l: 50, r: 20, t: 40, b: 80 },
}, CONFIG);
```

## 3. Drawdown (Underwater) Chart

Time series of peak-to-trough drawdown. Fill the worst entity.

```javascript
const traces = Object.entries(DATA.profiles).map(([p, d]) => ({
  x: d.dd_dates,
  y: d.dd_values.map(v => v * 100),  // ratio → percentage
  type: 'scatter', mode: 'lines',
  name: p + ' ' + NAMES[p],
  line: { color: COLORS[p], width: p === 'P5' ? 2 : 1.5 },
  fill: p === 'P5' ? 'tozeroy' : undefined,
  fillcolor: p === 'P5' ? 'rgba(220,38,38,0.08)' : undefined,
  hovertemplate: p + ': %{y:.1f}%<extra></extra>',
}));

// Crisis period shading
const shapes = [
  { x0: '2007-10-01', x1: '2009-03-01', label: 'GFC' },
  { x0: '2000-03-01', x1: '2002-09-01', label: 'Dotcom' },
].map(s => ({
  type: 'rect', xref: 'x', yref: 'paper',
  x0: s.x0, x1: s.x1, y0: 0, y1: 1,
  fillcolor: 'rgba(220,38,38,0.05)', line: { width: 0 },
}));

Plotly.newPlot('dd-chart', traces, {
  ...LAYOUT_BASE, height: 380,
  xaxis: { gridcolor: '#E5E7EB' },
  yaxis: { title: 'Drawdown (%)', gridcolor: '#E5E7EB', ticksuffix: '%' },
  legend: { orientation: 'h', y: 1.1, x: 0.5, xanchor: 'center' },
  shapes: shapes,
}, CONFIG);
```

## 4. Cumulative Growth (Log Scale)

Growth of $1 over time on log scale.

```javascript
const traces = Object.entries(DATA.profiles).map(([p, d]) => ({
  x: d.cum_dates,
  y: d.cum_values,
  type: 'scatter', mode: 'lines',
  name: p,
  line: { color: COLORS[p], width: 1.5 },
  hovertemplate: p + ': $%{y:.2f}<extra></extra>',
}));

Plotly.newPlot('cum-chart', traces, {
  ...LAYOUT_BASE, height: 320,
  xaxis: { gridcolor: '#E5E7EB' },
  yaxis: {
    title: 'Growth of $1', type: 'log',
    gridcolor: '#E5E7EB', tickprefix: '$',
  },
  legend: { orientation: 'h', y: 1.1, x: 0.5, xanchor: 'center' },
}, CONFIG);
```

## 5. Risk-Return Scatter

All portfolios as dots colored by a third metric, with selected entities highlighted as diamonds.

```javascript
// Background: all simulated portfolios
const bgTrace = {
  x: DATA.sim_scatter.vol,
  y: DATA.sim_scatter.ret,
  mode: 'markers', name: 'All portfolios',
  marker: {
    size: 5,
    color: DATA.sim_scatter.max_dd,
    colorscale: [[0, '#DC2626'], [0.5, '#D97706'], [1, '#059669']],
    cmin: -50, cmax: 0,
    colorbar: { title: 'Max DD', ticksuffix: '%', len: 0.6 },
    opacity: 0.5,
  },
  hovertemplate: 'Vol: %{x:.1f}%, Ret: %{y:.1f}%<br>DD: %{marker.color:.1f}%<extra></extra>',
};

// Foreground: selected entities as diamonds
const fgTraces = Object.entries(DATA.profiles).map(([p, d]) => ({
  x: [d.full.ann_vol * 100],
  y: [d.full.ann_return * 100],
  mode: 'markers+text', name: p,
  text: [p], textposition: 'top center',
  textfont: { size: 12, color: COLORS[p] },
  marker: {
    size: 14, color: COLORS[p],
    line: { width: 2, color: 'white' },
    symbol: 'diamond',
  },
}));

Plotly.newPlot('scatter-chart', [bgTrace, ...fgTraces], {
  ...LAYOUT_BASE, height: 450, showlegend: false,
  xaxis: { title: 'Annualized Volatility (%)', gridcolor: '#E5E7EB' },
  yaxis: { title: 'Annualized Return (%)', gridcolor: '#E5E7EB' },
}, CONFIG);
```

## 6. Correlation Heatmap

```javascript
const c = DATA.correlation;
Plotly.newPlot('corr-chart', [{
  z: c.values, x: c.labels, y: c.labels,
  type: 'heatmap',
  colorscale: [[0, '#DC2626'], [0.5, '#FFFFFF'], [1, '#2563EB']],
  zmin: -0.2, zmax: 1,
  text: c.values.map(r => r.map(v => v.toFixed(2))),
  texttemplate: '%{text}',
  hoverinfo: 'skip',
}], {
  ...LAYOUT_BASE, height: 280,
  margin: { l: 80, r: 20, t: 10, b: 40 },
  xaxis: { type: 'category', tickfont: { size: 11 } },
  yaxis: { type: 'category', tickfont: { size: 11 } },
}, CONFIG);
```

## 7. Bullet/Range Chart — Bounds & Corridors

Shows a range (bar) with a point value (diamond marker). Good for tactical bounds or confidence intervals.

```javascript
const traces = [];
categories.forEach((cat, ci) => {
  // Range bar (min to max)
  traces.push({
    x: entities,
    y: entities.map(e => bounds[cat][e][2] - bounds[cat][e][0]),  // range width
    base: entities.map(e => bounds[cat][e][0]),                    // start at min
    type: 'bar', name: cat + ' range',
    marker: { color: catColors[cat], opacity: 0.3 },
    text: entities.map(e => bounds[cat][e][0] + '–' + bounds[cat][e][2] + '%'),
    textposition: 'outside', textfont: { size: 9, color: catColors[cat] },
    showlegend: false,
    xaxis: ci === 0 ? 'x' : 'x' + (ci + 1),
    yaxis: ci === 0 ? 'y' : 'y' + (ci + 1),
  });

  // SAA marker (diamond)
  traces.push({
    x: entities,
    y: entities.map(e => bounds[cat][e][1]),  // SAA value
    type: 'scatter', mode: 'markers', name: cat + ' SAA',
    marker: {
      color: catColors[cat], size: 10, symbol: 'diamond',
      line: { width: 1, color: 'white' },
    },
    showlegend: false,
    xaxis: ci === 0 ? 'x' : 'x' + (ci + 1),
    yaxis: ci === 0 ? 'y' : 'y' + (ci + 1),
  });
});

Plotly.newPlot('bounds-chart', traces, {
  ...LAYOUT_BASE, height: 400,
  grid: { rows: 1, columns: categories.length, pattern: 'independent' },
  annotations: categories.map((cat, i) => ({
    text: '<b>' + cat + '</b>',
    font: { size: 13, color: catColors[cat] },
    xref: i === 0 ? 'x domain' : 'x' + (i + 1) + ' domain',
    yref: i === 0 ? 'y domain' : 'y' + (i + 1) + ' domain',
    x: 0.5, y: 1.12, showarrow: false, xanchor: 'center',
  })),
}, CONFIG);
```

## 8. Paired Bar — Full vs Recent Period

Side-by-side bars comparing two time periods.

```javascript
const traces = [
  {
    x: entities, y: entities.map(e => DATA.profiles[e].full.metric * 100),
    name: 'Full (1968-2025)', type: 'bar',
    marker: { color: '#2563EB' },
    text: entities.map(e => pct(DATA.profiles[e].full.metric)),
    textposition: 'outside',
  },
  {
    x: entities, y: entities.map(e => DATA.profiles[e].recent.metric * 100),
    name: 'Recent (2000-2025)', type: 'bar',
    marker: { color: '#93C5FD' },
    text: entities.map(e => pct(DATA.profiles[e].recent.metric)),
    textposition: 'outside',
  },
];

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'group', height: 280,
  yaxis: { ticksuffix: '%', gridcolor: '#E5E7EB' },
  legend: { orientation: 'h', y: 1.15, x: 0.5, xanchor: 'center' },
}, CONFIG);
```

## 9. HTML Gradient Table

JS-built table with background colors interpolated from best to worst.

```javascript
function lerpColor(t) {
  // t=0 best (blue), t=0.5 mid (amber), t=1 worst (red)
  const stops = [
    [0, [219, 234, 254]],     // #DBEAFE
    [0.5, [254, 243, 199]],   // #FEF3C7
    [1, [254, 226, 226]],     // #FEE2E2
  ];
  let lo = stops[0], hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) {
      lo = stops[i]; hi = stops[i + 1]; break;
    }
  }
  const f = hi[0] === lo[0] ? 0 : (t - lo[0]) / (hi[0] - lo[0]);
  const r = Math.round(lo[1][0] + (hi[1][0] - lo[1][0]) * f);
  const g = Math.round(lo[1][1] + (hi[1][1] - lo[1][1]) * f);
  const b = Math.round(lo[1][2] + (hi[1][2] - lo[1][2]) * f);
  return `rgb(${r},${g},${b})`;
}

// metrics: [label, jsonKey, decimals, isPercent, direction]
const metrics = [
  ['Ann. Return', 'ann_return', 1, true, 'higher'],
  ['Max Drawdown', 'max_dd', 1, true, 'lower'],
  ['Sharpe', 'sharpe', 2, false, 'higher'],
  // ...
];

let html = '<table class="metrics-table" style="table-layout:fixed;">';
html += '<thead><tr><th style="width:200px;">Metric</th>';
for (const e of entities) html += `<th>${e}</th>`;
html += '</tr></thead><tbody>';

for (const [label, key, dec, isPct, dir] of metrics) {
  const vals = entities.map(e => DATA.profiles[e].full[key]);
  const mn = Math.min(...vals), mx = Math.max(...vals);
  html += `<tr><td style="font-weight:500;">${label}</td>`;
  for (let i = 0; i < entities.length; i++) {
    const v = vals[i];
    const formatted = isPct ? pct(v, dec) : v.toFixed(dec);
    let t = mx === mn ? 0.5 : (v - mn) / (mx - mn);
    if (dir === 'higher') t = 1 - t;
    html += `<td style="background:${lerpColor(t)};font-variant-numeric:tabular-nums;">${formatted}</td>`;
  }
  html += '</tr>';
}
html += '</tbody></table>';
document.getElementById('container-id').innerHTML = html;
```

## 10. Stacked Distribution Bar

For band/bucket distributions (e.g., drawdown depth bands).

```javascript
const bands = ['At peak', '0-1%', '1-2%', '2-3%', '3-5%', '5-10%', '>10%'];
const bandColors = ['#059669', '#10B981', '#6EE7B7', '#FCD34D', '#F59E0B', '#EF4444', '#991B1B'];

const traces = bands.map((band, i) => ({
  x: entities,
  y: entities.map(e => DATA.profiles[e].hwm_bands[i]),
  name: band, type: 'bar',
  marker: { color: bandColors[i] },
  hovertemplate: '%{x}: %{y:.1f}% ' + band + '<extra></extra>',
}));

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'stack', height: 300,
  yaxis: { title: '% of Time', ticksuffix: '%', gridcolor: '#E5E7EB' },
  legend: { orientation: 'h', y: 1.2, x: 0.5, xanchor: 'center', font: { size: 9 } },
}, CONFIG);
```

## Subplot Patterns

### Independent Subplots (Side-by-Side)

```javascript
// Use grid layout for independent axes
layout.grid = { rows: 1, columns: N, pattern: 'independent' };

// Assign traces to subplots
trace.xaxis = i === 0 ? 'x' : 'x' + (i + 1);
trace.yaxis = i === 0 ? 'y' : 'y' + (i + 1);

// Title annotations above each subplot
layout.annotations = items.map((item, i) => ({
  text: '<b>' + item + '</b>',
  xref: i === 0 ? 'x domain' : 'x' + (i + 1) + ' domain',
  yref: i === 0 ? 'y domain' : 'y' + (i + 1) + ' domain',
  x: 0.5, y: 1.12, showarrow: false, xanchor: 'center',
}));
```

## 11. Crisis Comparison Bars

Grouped bars comparing benchmark vs strategy with a protection delta bar. Common for TAA/strategy evaluation.

```javascript
const names = DATA.crises.map(c => c.name);
const saaVals = DATA.crises.map(c => c.saa_return * 100);
const taaVals = DATA.crises.map(c => c.taa_return * 100);
const protection = DATA.crises.map(c => c.protection * 100);

const traces = [
  { x: names, y: saaVals, name: 'Benchmark', type: 'bar', marker: { color: '#0EA5E9' },
    text: saaVals.map(v => v.toFixed(1) + '%'), textposition: 'outside' },
  { x: names, y: taaVals, name: 'Strategy', type: 'bar', marker: { color: '#10B981' },
    text: taaVals.map(v => v.toFixed(1) + '%'), textposition: 'outside' },
  { x: names, y: protection, name: 'Protection', type: 'bar',
    marker: { color: protection.map(v => v >= 0 ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'),
      line: { color: protection.map(v => v >= 0 ? '#10B981' : '#EF4444'), width: 2 } },
    text: protection.map(v => (v >= 0 ? '+' : '') + v.toFixed(2) + '%'),
    textposition: 'outside',
    textfont: { color: protection.map(v => v >= 0 ? '#059669' : '#DC2626') } },
];

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'group',
  xaxis: { type: 'category' },  // MANDATORY for string labels
  yaxis: { title: 'Return (%)', ticksuffix: '%' },
  shapes: [{ type: 'line', x0: -0.5, x1: names.length - 0.5, y0: 0, y1: 0,
    line: { color: '#64748B', width: 1.5 } }],
  legend: { orientation: 'h', y: 1.08, x: 0.5, xanchor: 'center' },
}, CONFIG);
```

## 12. Conditional Performance (Up/Down Market Split)

Shows annualized excess returns split by market regime. Color-codes bars by sign.

```javascript
const traces = [
  { x: entities, y: entities.map(e => DATA[e].excess_down * 100),
    name: 'Down markets', type: 'bar',
    marker: { color: entities.map(e => DATA[e].excess_down >= 0 ? '#10B981' : '#EF4444') },
    text: entities.map(e => (DATA[e].excess_down >= 0 ? '+' : '') + (DATA[e].excess_down * 100).toFixed(2) + '%'),
    textposition: 'outside' },
  { x: entities, y: entities.map(e => DATA[e].excess_up * 100),
    name: 'Up markets', type: 'bar',
    marker: { color: entities.map(e => DATA[e].excess_up >= 0 ? '#10B981' : '#F59E0B') },
    text: entities.map(e => (DATA[e].excess_up >= 0 ? '+' : '') + (DATA[e].excess_up * 100).toFixed(2) + '%'),
    textposition: 'outside' },
];

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE, barmode: 'group',
  xaxis: { type: 'category' },
  yaxis: { title: 'Ann. Excess Return (%)', ticksuffix: '%' },
  shapes: [{ type: 'line', x0: -0.5, x1: entities.length - 0.5, y0: 0, y1: 0,
    line: { color: '#64748B', width: 1.5 } }],
}, CONFIG);
```

## 13. Signal Heatmap (Time × Category)

Diverging heatmap for signal scores or z-scores. Reversed y-axis for chronological top-to-bottom.

```javascript
Plotly.newPlot('chart-id', [{
  z: DATA.heatmap.values,
  x: DATA.heatmap.categories,
  y: DATA.heatmap.dates,
  type: 'heatmap',
  colorscale: [[0,'#DC2626'],[0.25,'#FCA5A5'],[0.5,'#F9FAFB'],[0.75,'#86EFAC'],[1,'#16A34A']],
  zmin: -4, zmax: 4,  // symmetric range
  colorbar: { title: 'Score', thickness: 12, len: 0.6 },
  hovertemplate: '%{x}<br>%{y|%Y-%m}: %{z:.1f}<extra></extra>',
}], {
  ...LAYOUT_BASE,
  margin: { l: 80, r: 20, t: 20, b: 80 },
  yaxis: { autorange: 'reversed' },
}, CONFIG);
```

## 14. Regime Timeline (Multi-Line with Threshold Bands)

Multiple time series with bull/bear threshold bands as dashed horizontal lines.

```javascript
const l0s = ['FI_SHORT', 'FI_AGG', 'EQ', 'COM'];
const colors = { FI_SHORT: '#7DD3FC', FI_AGG: '#2563EB', EQ: '#16A34A', COM: '#F59E0B' };

const traces = l0s.map(l0 => ({
  x: DATA.regimes.map(r => r.date),
  y: DATA.regimes.map(r => r.l0_scores[l0]),
  name: l0, type: 'scatter', mode: 'lines',
  line: { color: colors[l0], width: 1.5 },
}));

Plotly.newPlot('chart-id', traces, {
  ...LAYOUT_BASE,
  yaxis: { title: 'Mean Score' },
  shapes: [
    { type: 'line', x0: dates[0], x1: dates[dates.length-1], y0: 0.5, y1: 0.5,
      line: { color: '#16A34A', width: 1, dash: 'dot' } },  // bull threshold
    { type: 'line', x0: dates[0], x1: dates[dates.length-1], y0: -0.5, y1: -0.5,
      line: { color: '#DC2626', width: 1, dash: 'dot' } },  // bear threshold
  ],
  legend: { orientation: 'h', y: 1.1, x: 0.5, xanchor: 'center' },
}, CONFIG);
```

## Common Gotchas

1. **Ratio vs %**: JSON stores 0.057, chart needs 5.7. Always `.map(v => v * 100)`.
2. **`<extra></extra>`**: Add to every `hovertemplate` to hide the trace name box.
3. **Responsive**: Always pass `CONFIG` with `responsive: true`.
4. **Transparent bg**: `paper_bgcolor` and `plot_bgcolor` must be `'rgba(0,0,0,0)'` to blend with card backgrounds.
5. **Legend overlap**: Use `y: 1.1` or higher to push legend above chart area.
6. **Grid lines**: Always set `gridcolor: '#E5E7EB'` — Plotly defaults are too dark.
7. **MANDATORY — Categorical axes**: When using string labels (names, profiles, categories) on any axis, always set `type: 'category'` in the axis config. Without this, Plotly auto-detects and often parses strings as dates (showing Jan 1970 timestamps) or numbers. Apply to both `xaxis` and `yaxis` as needed:
   ```javascript
   xaxis: { type: 'category' }           // horizontal string labels
   yaxis: { type: 'category' }           // vertical string labels (e.g., correlation matrix)
   yaxis: { type: 'category', autorange: 'reversed' }  // horizontal bar charts
   ```
8. **Horizontal bar charts**: Need `orientation: 'h'` on traces AND `yaxis: { type: 'category', autorange: 'reversed' }` on layout. Without `autorange: 'reversed'`, categories appear bottom-to-top.
9. **Bar mode selection**: Use `barmode: 'group'` for comparison (side-by-side), `barmode: 'stack'` for composition (parts of whole). Never mix intentions.
