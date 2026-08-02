# `reporting` — shared self-contained HTML reporting library

> **Kit-mastered synced copy.** The canonical source is
> `dm-evo-lab/research/_lib/reporting/`; this is a bundled copy that travels with
> the `investment-research-dashboard` skill (no sync script in this repo — resync
> is a manual `cp`). Inside a research line the same tree is imported as
> `_lib.reporting`; bundled in the skill it's imported as `reporting`. Same code
> either way — the package uses relative imports.

One reporting library for every research line, so we stop having "every agent
roll its own dashboard". **Canonical templates: `backtest_dashboard`,
`research_story`; shared primitives in `base`.**

## The contract (non-negotiable)

1. **Always self-contained.** Plotly is inlined from the installed package
   (`base.inline_plotly()` → reads `plotly.min.js` from
   `plotly/package_data/`). **NEVER a CDN `<script src=...>`.** A rendered report
   must have zero external `<script>`, `<link>`, or `<img>` — it opens offline.
2. **The page never scrolls horizontally.** `body{overflow-x:hidden}`; every wide
   table/chart is wrapped in `.scroll-x` (its own `overflow-x:auto` box). Use
   `base.table(...)` and `base.plot(...)` (they wrap for you) or wrap manually.

## Public API

```python
from _lib.reporting import base, backtest_dashboard, research_story
```

### `base` — shared primitives (one source of truth)
- `inline_plotly() -> str` — the `<script>` with the vendored plotly bundle.
- `SHARED_CSS` — cards, tables, KPI row, sticky section nav, `.scroll-x`.
- `page(title, sections, *, favicon=None, subtitle=None, thesis=None, badges=None, ...) -> str`
  — assemble a full self-contained doc (inline CSS + inline plotly + sticky nav).
- `section(title, *, reasoning_html='', evidence_html='', step=None) -> dict`
  — a numbered section = a reasoning block + its evidence.
- `table(df, *, scroll=True, fmt=None) -> str` — HTML table wrapped in `.scroll-x`.
- `plot(fig_or_traces, layout, div_id, height=340) -> str` — a Plotly div + its
  `Plotly.newPlot` call against the inlined bundle.
- `kpi_row(items) -> str`, `banner(title, body, *, kind='') -> str`, `dumps(obj)`.

### `backtest_dashboard` — canonical backtest report (profile-agnostic)
`render(payload) -> str`. Per "profile" (any grouping key): equity overlay,
drawdown overlay, summary-metrics table, optional weight evolution. Helpers
`series_from_returns(...)` / `series_from_equity(...)` build series entries
straight from pandas. See the module docstring for the payload schema.

### `research_story` — step-by-step narrative
`render(sections, *, title, thesis, kpis, ...) -> str`. Title + thesis banner +
KPI row + numbered reasoning-block-plus-evidence sections + sticky nav. Helpers
`why(lead, body, kind=...)` and `card(title, inner, note=...)`.

## Importing

Plain package tree — no install needed; add its parent dir to `sys.path`.

**Bundled in the skill** (the copy next to this README):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # dir holding reporting/
from reporting import base, backtest_dashboard, research_story
```

**From a dm-evo-lab research line** (canonical source at `research/_lib/reporting/`):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[N]))  # the research/ dir
from _lib.reporting import base, backtest_dashboard, research_story
```

Only deps are `pandas`, `numpy`, `plotly` — already in every line's venv.

## Verify self-contained

```bash
grep -Eo '<(script|link|img)[^>]*(src|href)="https?://[^"]+"' report.html   # → no output
```
