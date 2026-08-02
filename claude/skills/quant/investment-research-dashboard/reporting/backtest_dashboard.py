"""The canonical backtest report — profile-agnostic.

``render(payload)`` produces a self-contained HTML dashboard. Per "profile"
(any grouping key — SAA profiles, strategies, universes...) it shows:

  1. equity overlay (strategy + benchmark series)
  2. drawdown overlay
  3. summary-metrics table
  4. optional weight-evolution stacked area

Generalized from ``research/saa-finalization/scratch/scripts/build_reports.py``
(``build_backtest_data``) and the (de-CDN'd) TAA ``simple_dashboard.py``.

Payload contract
----------------
::

    payload = {
        "title": str,
        "subtitle": str,               # optional
        "footer_html": str,            # optional
        "favicon": str,                # optional emoji
        "metrics_order": [(key, label, "num"|"pct", n_dp), ...],   # optional
        "profiles": {
            "<pid>": {
                "name": str,                      # optional display name
                "series": {
                    "<series label>": {
                        "dates": [...], "equity": [...],
                        "drawdown": [...],          # optional; else derived
                        "color": "#...", "dash": "dot"|None, "benchmark": bool,
                    },
                    ...
                },
                "metrics": { "<series label>": {metric: value, ...}, ... },
                "weights": {                        # optional
                    "series": "<series label>",     # which series the weights belong to
                    "dates": [...], "cats": [...], "values": [[...], ...],
                } ,
            },
            ...
        },
    }

Every series is drawn on the same equity/DD axes, so it works for any set of
strategies/benchmarks, not just SAA.
"""

from __future__ import annotations

import pandas as pd

from . import base

# ---------------------------------------------------------------------------
# payload helpers (build a payload straight from pandas objects)
# ---------------------------------------------------------------------------


def series_from_returns(
    rets: pd.Series,
    *,
    color: str,
    dash: str | None = None,
    benchmark: bool = False,
    subsample_n: int = 260,
) -> dict:
    """Build a series entry (equity + drawdown) from a daily/periodic return series."""
    r = rets.fillna(0.0)
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1.0
    eq = _subsample(eq, subsample_n)
    dd = dd.reindex(eq.index)
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in eq.index],
        "equity": [round(float(v), 5) for v in eq.values],
        "drawdown": [round(float(v), 5) for v in dd.values],
        "color": color,
        "dash": dash,
        "benchmark": benchmark,
    }


def series_from_equity(
    equity: pd.Series,
    *,
    color: str,
    dash: str | None = None,
    benchmark: bool = False,
    subsample_n: int = 260,
) -> dict:
    """Build a series entry from an equity (growth-of-1) curve."""
    # compute drawdown on the FULL series (so a peak skipped by subsampling can't
    # understate max DD), then reindex to the sampled dates — matches
    # series_from_returns().
    dd_full = equity / equity.cummax() - 1.0
    eq = _subsample(equity, subsample_n)
    dd = dd_full.reindex(eq.index)
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in eq.index],
        "equity": [round(float(v), 5) for v in eq.values],
        "drawdown": [round(float(v), 5) for v in dd.values],
        "color": color,
        "dash": dash,
        "benchmark": benchmark,
    }


def _subsample(s: pd.Series, n: int) -> pd.Series:
    if len(s) <= n:
        return s
    step = max(1, len(s) // n)
    sub = s.iloc[::step]
    # preserve both the global minimum AND the max-drawdown trough (deepest point
    # below the running peak) — the two can differ when a later dip falls from a
    # higher peak, and the drawdown chart must not miss its trough.
    keep = {s.idxmin(), (s / s.cummax() - 1.0).idxmin()}
    missing = [i for i in keep if i not in sub.index]
    if missing:
        sub = pd.concat([sub, s.loc[missing]]).sort_index()
    return sub


DEFAULT_METRICS_ORDER = [
    ("CAGR", "CAGR", "pct", 2),
    ("Vol", "Vol", "pct", 2),
    ("Sharpe", "Sharpe", "num", 3),
    ("Sortino", "Sortino", "num", 3),
    ("Calmar", "Calmar", "num", 3),
    ("MaxDD", "Max DD", "pct", 1),
    ("IR", "IR", "num", 3),
]


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

_SCRIPT = r"""
const D = PAYLOAD;
const LB = {font:{family:"-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif",size:11.5},
  paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',margin:{l:52,r:16,t:24,b:34}};
const CFG={responsive:true,displayModeBar:false};
function pct(v,d){return v==null?'—':(v*100).toFixed(d==null?1:d)+'%';}
function num(v,d){return v==null?'—':Number(v).toFixed(d==null?3:d);}
function fmtMetric(v,kind,dp){return kind==='pct'?pct(v,dp):num(v,dp);}
// drawdown is optional per the payload contract — derive from equity when absent
function ddOf(s){
  if(s.drawdown) return s.drawdown;
  let peak=-Infinity;
  return (s.equity||[]).map(v=>{ if(v==null) return null; if(v>peak) peak=v; return peak>0?v/peak-1:0; });
}

Object.keys(D.profiles).forEach(pid=>{
  const prof=D.profiles[pid];
  const dom=(D.dom&&D.dom[pid])||pid;   // sanitized DOM id (matches the HTML anchors)
  const labels=Object.keys(prof.series);
  // equity overlay
  const eqTraces=labels.map(lab=>{
    const s=prof.series[lab];
    return {x:s.dates,y:s.equity,name:lab,mode:'lines',
      line:{color:s.color,width:s.benchmark?1.4:2,dash:s.dash||'solid'}};
  });
  Plotly.newPlot('eq_'+dom,eqTraces,{...LB,legend:{orientation:'h',y:1.14,x:0.5,xanchor:'center',font:{size:10}},
    yaxis:{title:'growth of 1',gridcolor:'#E5E7EB'},xaxis:{gridcolor:'#E5E7EB'}},CFG);
  // drawdown overlay
  const ddTraces=labels.map(lab=>{
    const s=prof.series[lab];
    return {x:s.dates,y:ddOf(s).map(v=>v==null?null:v*100),name:lab,mode:'lines',
      fill:s.benchmark?'none':'tozeroy',line:{color:s.color,width:s.benchmark?1.2:1.4,dash:s.dash||'solid'}};
  });
  Plotly.newPlot('dd_'+dom,ddTraces,{...LB,legend:{orientation:'h',y:1.14,x:0.5,xanchor:'center',font:{size:10}},
    yaxis:{ticksuffix:'%',gridcolor:'#E5E7EB'},xaxis:{gridcolor:'#E5E7EB'}},CFG);
  // weight evolution (optional)
  if(prof.weights){
    const w=prof.weights;
    const stack=w.cats.map((cat,i)=>({x:w.dates,y:w.values.map(row=>row[i]),name:cat,
      type:'scatter',mode:'lines',stackgroup:'one',hovertemplate:'%{y:.1%}<extra>%{fullData.name}</extra>'}));
    Plotly.newPlot('wt_'+dom,stack,{...LB,legend:{orientation:'h',y:-0.18,font:{size:9}},
      yaxis:{tickformat:'.0%',range:[0,1],gridcolor:'#E5E7EB'},xaxis:{gridcolor:'#E5E7EB'}},CFG);
  }
});
"""


def _dom_ids(profiles: dict) -> dict:
    """Map each profile key to a sanitized, unique DOM id (attribute-safe).

    Profile keys come from caller data, so they can contain quotes/spaces that
    would break ``id="..."`` attributes or produce invalid DOM ids. Slug them
    and de-dup so the HTML anchors and the JS ``Plotly.newPlot`` targets agree.
    """
    seen: dict[str, int] = {}
    out: dict = {}
    for i, pid in enumerate(profiles):
        slug = base._slug(str(pid)) or f"p{i}"
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        out[pid] = slug if n == 0 else f"{slug}-{n}"
    return out


def render(payload: dict) -> str:
    """Render the canonical backtest dashboard to a self-contained HTML string."""
    metrics_order = payload.get("metrics_order") or DEFAULT_METRICS_ORDER
    # Normalize profile keys to strings up front: JSON object keys are strings,
    # so 1 and "1" would collide in the browser and silently drop a profile.
    profiles = {}
    for k, v in payload["profiles"].items():
        sk = str(k)
        if sk in profiles:
            raise ValueError(f"duplicate profile id after string-normalization: {sk!r}")
        profiles[sk] = v
    dom = _dom_ids(profiles)

    sections = []
    for pid, prof in profiles.items():
        did = dom[pid]
        name = prof.get("name", pid)
        labels = list(prof["series"].keys())
        metrics = prof.get("metrics", {})

        # metrics table
        mt_head = "<th>metric</th>" + "".join(
            f"<th>{base._esc(lab)}</th>" for lab in labels
        )
        mt_rows = []
        for key, lbl, kind, dp in metrics_order:
            cells = []
            for lab in labels:
                v = metrics.get(lab, {}).get(key)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    disp = "—"
                elif kind == "pct":
                    disp = f"{v * 100:.{dp}f}%"
                else:
                    disp = f"{float(v):.{dp}f}"
                cells.append(f"<td>{disp}</td>")
            mt_rows.append(f"<tr><td>{base._esc(str(lbl))}</td>{''.join(cells)}</tr>")
        metrics_table = (
            f'<div class="scroll-x"><table class="t"><thead><tr>{mt_head}</tr></thead>'
            f"<tbody>{''.join(mt_rows)}</tbody></table></div>"
        )

        weight_card = ""
        if prof.get("weights"):
            wlab = prof["weights"].get("series", labels[-1])
            weight_card = (
                f'<div class="card"><h3>Weight evolution — {base._esc(str(wlab))} (stacked)</h3>'
                f'<div class="scroll-x"><div id="wt_{did}" style="height:360px;min-width:340px"></div></div></div>'
            )

        evidence = f"""
<div class="chart-row">
  <div class="chart-box"><h3>Equity (growth of 1)</h3>
    <div class="scroll-x"><div id="eq_{did}" style="height:300px;min-width:320px"></div></div></div>
  <div class="chart-box"><h3>Drawdown</h3>
    <div class="scroll-x"><div id="dd_{did}" style="height:300px;min-width:320px"></div></div></div>
</div>
<div class="card"><h3>Summary metrics</h3>{metrics_table}</div>
{weight_card}
"""
        sections.append(base.section(f"{pid} — {name}", evidence_html=evidence))

    # report-specific extra sections (e.g. a shadow-turnover reference) rendered
    # after the per-profile sections; each is a base.section(...) dict.
    for extra in payload.get("extra_sections", []):
        sections.append(extra)

    # Only the per-profile chart DATA is embedded for the runtime script — never
    # the HTML-bearing keys (extra_sections/footer/subtitle), whose nested
    # <script>/quotes would corrupt this outer script block.
    client = {"profiles": payload["profiles"], "dom": dom}
    extra_script = f"const PAYLOAD={base.dumps(client)};\n{_SCRIPT}"

    return base.page(
        payload["title"],
        sections,
        favicon=payload.get("favicon", "📈"),
        subtitle=payload.get("subtitle"),
        footer_html=payload.get("footer_html", ""),
        extra_script=extra_script,
    )
