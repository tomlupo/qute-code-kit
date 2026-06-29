# CSS Components Reference

Complete CSS for the dashboard layout system. Copy and adapt for new dashboards.

## CSS Variables

```css
:root {
  --primary: #0C2340;
  --primary-light: #1F3A5F;
  --accent: #2563EB;
  --accent-soft: #DBEAFE;
  --bg: #FFFFFF;
  --bg-alt: #F9FAFB;
  --surface: #F1F5F9;
  --text: #0F172A;
  --text-muted: #6B7280;
  --border: #E5E7EB;
  --error: #DC2626;
  --success: #16A34A;
  --warning: #D97706;
}
```

These are the default (professional finance) theme. A brand skill overrides these values.

## Reset & Body

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
```

## Header

```css
.header {
  background: var(--primary);
  color: white;
  padding: 48px 32px 36px;
}
.header h1 { font-size: 2.5rem; font-weight: 700; line-height: 1.1; }
.header .subtitle { color: rgba(255,255,255,0.7); font-size: 1rem; margin-top: 8px; }
```

## Sticky Navigation

```css
.nav {
  position: sticky; top: 0; z-index: 100; background: white;
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex; gap: 0; overflow-x: auto;
}
.nav a {
  padding: 12px 16px; font-size: 0.8rem; font-weight: 500;
  color: var(--text-muted); text-decoration: none; white-space: nowrap;
  border-bottom: 2px solid transparent; transition: all 0.15s;
}
.nav a:hover, .nav a.active { color: var(--accent); border-bottom-color: var(--accent); }
```

## Container & Sections

```css
.container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
.section {
  padding: 48px 0 32px;
  border-bottom: 1px solid var(--border);
}
.section:last-child { border-bottom: none; }
.section h2 {
  font-size: 1.5rem; font-weight: 700; color: var(--primary);
  margin-bottom: 8px;
}
.section .section-desc {
  color: var(--text-muted); font-size: 0.875rem; margin-bottom: 24px; max-width: 720px;
}
```

## KPI Cards

```css
.kpi-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.kpi {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 20px; flex: 1; min-width: 140px; text-align: center;
}
.kpi .kpi-value { font-size: 1.5rem; font-weight: 700; color: var(--primary); }
.kpi .kpi-label { font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; }
```

## Chart Layout

```css
.chart-row { display: flex; gap: 24px; flex-wrap: wrap; }
.chart-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  flex: 1; min-width: 320px;
}
.chart-box.full { flex-basis: 100%; }
.chart-box h3 {
  font-size: 1rem; font-weight: 600; color: var(--primary);
  margin-bottom: 12px;
}
.chart-box .chart-note {
  font-size: 0.75rem; color: var(--text-muted); margin-top: 8px;
}
```

### Layout Control with Flex

```html
<!-- Two charts, 2:1 ratio -->
<div class="chart-row">
  <div class="chart-box" style="flex:2;">Wide chart</div>
  <div class="chart-box" style="flex:1;">Narrow chart</div>
</div>

<!-- Full-width chart -->
<div class="chart-box full">
  <div id="my-chart"></div>
</div>

<!-- Two-column grid -->
<div class="two-col">
  <div class="chart-box">Left</div>
  <div class="chart-box">Right</div>
</div>
```

## Data Tables

```css
.metrics-table {
  width: 100%; border-collapse: collapse; font-size: 0.8rem;
}
.metrics-table th, .metrics-table td {
  padding: 8px 12px; text-align: right; border-bottom: 1px solid var(--border);
}
.metrics-table th { font-weight: 600; color: var(--primary); background: var(--surface); }
.metrics-table th:first-child, .metrics-table td:first-child { text-align: left; }
.metrics-table tr:hover td { background: var(--accent-soft); }
```

### Fixed-layout table (for many columns)

```css
.metrics-table.fixed { table-layout: fixed; }
.metrics-table.fixed th,
.metrics-table.fixed td { text-align: center; padding: 6px 4px; font-size: 0.75rem; }
```

## Allocation Cards (Grid)

```css
.alloc-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }
.alloc-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 16px; text-align: center;
}
.alloc-card .profile-name {
  font-size: 0.875rem; font-weight: 600; color: var(--primary);
  margin-bottom: 4px;
}
.alloc-card .profile-label {
  font-size: 0.7rem; color: var(--text-muted); margin-bottom: 12px;
}
.alloc-bar { height: 24px; border-radius: 4px; overflow: hidden; display: flex; margin-bottom: 8px; }
.alloc-bar span { display: block; height: 100%; }
.alloc-legend { font-size: 0.7rem; color: var(--text-muted); text-align: left; }
.alloc-legend div { display: flex; align-items: center; gap: 4px; margin: 2px 0; }
.alloc-legend .dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
```

## Insight Box (Callout)

```css
.insight-box {
  background: var(--accent-soft); border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0; padding: 12px 16px; margin-top: 16px;
  font-size: 0.8rem; color: var(--primary);
}
.insight-box strong { color: var(--accent); }
```

## Chips / Tags

```css
.chip {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600;
}
```

## Footer

```css
.footer {
  background: var(--bg-alt); padding: 24px 32px; text-align: center;
  font-size: 0.75rem; color: var(--text-muted);
}
```

## Two-Column Grid

```css
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
```

## Responsive Breakpoints

```css
@media (max-width: 768px) {
  .alloc-grid { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .chart-row { flex-direction: column; }
  .header h1 { font-size: 1.75rem; }
}
```
