"""Shared primitives for self-contained HTML research reports.

NON-NEGOTIABLE CONTRACT
-----------------------
* **Always self-contained.** ``inline_plotly()`` reads ``plotly.min.js`` from the
  installed plotly package and embeds it. NEVER a CDN ``<script src=...>``.
* **The page never scrolls horizontally.** ``body{overflow-x:hidden}`` and every
  wide table/chart is wrapped in ``.scroll-x`` (its own ``overflow-x:auto`` box).

These primitives are the single source of truth every report template
(``backtest_dashboard``, ``research_story``) and every bespoke builder should
route through, so "every agent rolls its own dashboard" stops being a thing.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# self-contained plotly — the one source of truth for de-CDN'ing
# ---------------------------------------------------------------------------


def plotly_min_js_path() -> Path:
    """Path to the vendored ``plotly.min.js`` inside the installed plotly package."""
    import plotly

    return Path(plotly.__file__).parent / "package_data" / "plotly.min.js"


def inline_plotly() -> str:
    """Return ``<script>…plotly.min.js…</script>`` read from the installed package.

    Self-contained by construction: no network, no CDN. This is the ONE function
    every report uses to embed Plotly.
    """
    js = plotly_min_js_path().read_text(encoding="utf-8")
    return f"<script>{js}</script>"


# ---------------------------------------------------------------------------
# JSON helpers (NaN/Inf -> null so the embedded payload is valid JSON)
# ---------------------------------------------------------------------------


def _clean(o):
    """Recursively replace NaN/Inf with None so ``json.dumps`` emits valid JSON."""
    if isinstance(o, float):
        return None if (np.isnan(o) or np.isinf(o)) else o
    if isinstance(o, (np.floating,)):
        return _clean(float(o))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_clean(v) for v in o.tolist()]
    return o


def dumps(o) -> str:
    """Compact JSON with NaN/Inf scrubbed to null.

    Safe to embed inside a ``<script>`` block: ``</`` (and the U+2028/U+2029
    line separators) are escaped so payload data containing ``</script>`` cannot
    terminate the script element or inject markup.
    """
    s = json.dumps(_clean(o), separators=(",", ":"))
    return (
        s.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# ---------------------------------------------------------------------------
# shared CSS — cards, tables, KPI row, sticky nav, scroll-x wrapper
# ---------------------------------------------------------------------------

SHARED_CSS = """
:root{
  --primary:#0C2340;--accent:#2563EB;--bg:#F4F6F9;--card:#FFFFFF;--muted:#6B7280;
  --line:#E5E7EB;--good:#059669;--bad:#DC2626;--warn:#D97706;--wash:#F8FAFC;
}
*{box-sizing:border-box}
/* CONTRACT: the page never scrolls horizontally (both html + body clip x) */
html{scroll-behavior:smooth;overflow-x:hidden}
body{
  margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  color:#111827;background:var(--bg);line-height:1.5;
  overflow-x:hidden;
}

/* ---- header ---- */
.header{background:linear-gradient(135deg,#0C2340,#12325c);color:#fff;padding:38px 24px 32px}
.header .wrap{max-width:1180px;margin:0 auto}
.header .eyebrow{color:#7FA9E6;font-size:12px;font-weight:700;letter-spacing:.09em;text-transform:uppercase}
.header h1{margin:8px 0 8px;font-size:26px;line-height:1.25}
.header .subtitle{color:#D6E2F4;font-size:14px;margin:0 0 8px;max-width:820px}
.header .sub{color:#9DB2CE;font-size:12.5px}
.header .thesis{font-size:16px;color:#D6E2F4;font-style:italic;margin:6px 0 14px;max-width:780px}
.header .badges{margin-top:14px;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);border-radius:999px;
  padding:5px 13px;font-size:12px;color:#EAF1FB}
.badge b{color:#fff}

/* ---- sticky section nav ---- */
.nav{position:sticky;top:0;background:rgba(255,255,255,.96);backdrop-filter:blur(6px);
  border-bottom:1px solid var(--line);z-index:20;overflow-x:auto;white-space:nowrap}
.nav .wrap{max-width:1180px;margin:0 auto;padding:0 12px}
.nav a{display:inline-block;padding:13px 13px;color:var(--muted);text-decoration:none;font-size:12.5px;font-weight:600}
.nav a:hover{color:var(--accent)}

/* ---- layout ---- */
.container{max-width:1180px;margin:0 auto;padding:0 20px}
.section{padding:34px 0;border-bottom:1px solid var(--line)}
.section h2{color:var(--primary);font-size:21px;margin:0 0 6px}
.section-desc{color:var(--muted);font-size:13px;margin:0 0 16px;max-width:920px;line-height:1.55}
.step{display:inline-block;background:var(--accent);color:#fff;font-size:12px;font-weight:700;
  border-radius:6px;padding:3px 9px;margin-bottom:10px}

/* ---- reasoning block ---- */
.why{background:var(--wash);border-left:4px solid var(--accent);border-radius:0 10px 10px 0;
  padding:15px 20px;margin:14px 0 18px;font-size:14px;line-height:1.6;max-width:940px}
.why.warn{border-left-color:var(--warn);background:#FFFBEB}
.why.good{border-left-color:var(--good);background:#F0FDF4}
.why b{color:var(--primary)}
.why .lead{font-weight:700;color:var(--primary);display:block;margin-bottom:4px;font-size:14.5px}

/* ---- cards ---- */
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0;
  box-shadow:0 1px 2px rgba(16,24,40,.04)}
.card h3{margin:0 0 10px;font-size:14px;color:var(--primary)}
.chart-row{display:flex;gap:16px;flex-wrap:wrap}
.chart-box{flex:1;min-width:360px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.chart-box.full{flex-basis:100%}
.chart-box h3{margin:0 0 8px;font-size:14px;color:var(--primary)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:16px}

/* ---- CONTRACT: wide content scrolls inside its OWN box, never the page ---- */
.scroll-x{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}

/* ---- tables ---- */
table.t{border-collapse:collapse;font-size:12.5px;background:var(--card);min-width:100%}
table.t th,table.t td{padding:8px 11px;border-bottom:1px solid var(--line);text-align:right;
  font-variant-numeric:tabular-nums;white-space:nowrap}
table.t th:first-child,table.t td:first-child{text-align:left}
table.t thead th{background:#F3F4F6;color:var(--primary);position:sticky;top:0}
.pass{color:var(--good);font-weight:700}.fail{color:var(--bad);font-weight:700}
.pos{color:var(--good);font-weight:600}.neg{color:var(--bad);font-weight:600}
.muted{color:var(--muted)}

/* ---- chips / banners ---- */
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;background:#EFF6FF;color:var(--accent)}
.chip.new{background:#FEF3C7;color:#92400E}
.banner{border-left:4px solid var(--accent);background:var(--wash);padding:14px 18px;border-radius:0 10px 10px 0;margin:16px 0;font-size:13px;line-height:1.55}
.banner.warn{border-left-color:var(--warn);background:#FFFBEB}
.banner.good{border-left-color:var(--good);background:#F0FDF4}
.banner b{color:var(--primary)}
.banner h4{margin:0 0 6px;color:var(--primary);font-size:14px}

/* ---- KPI row ---- */
.kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 16px}
.kpi{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:15px}
.kpi .v{font-size:22px;font-weight:800;color:var(--primary)}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:4px}
.kpi.good .v{color:var(--good)}.kpi.bad .v{color:var(--bad)}.kpi.warn .v{color:var(--warn)}

/* ---- footer ---- */
.footer{padding:28px 20px 48px;color:var(--muted);font-size:12px;text-align:center;max-width:940px;margin:0 auto}
"""


# ---------------------------------------------------------------------------
# building blocks
# ---------------------------------------------------------------------------


def _slug(title: str) -> str:
    keep = "".join(c if (c.isalnum() or c == " ") else " " for c in title)
    return "-".join(keep.lower().split()) or "section"


def section(
    title: str,
    *,
    reasoning_html: str = "",
    evidence_html: str = "",
    step: str | None = None,
    id: str | None = None,
    nav_label: str | None = None,
) -> dict:
    """A numbered section = a reasoning block (the WHY) + its evidence (the WHAT).

    Returns a dict consumed by :func:`page`; ``id`` defaults to a slug of the
    title (the sticky-nav anchor) but can be pinned to preserve existing anchors.
    ``nav_label`` overrides the text shown in the nav (else the title is used).
    ``step`` renders an optional pill label.
    """
    return {
        "id": id or _slug(title),
        "title": title,
        "nav_label": nav_label,
        "step": step,
        "reasoning_html": reasoning_html,
        "evidence_html": evidence_html,
    }


def _section_html(sec: dict) -> str:
    # title/step are plain text -> HTML-escape; id is an attribute -> slug it.
    # Only reasoning_html/evidence_html are trusted raw HTML (caller-built).
    step = (
        f'<span class="step">{_esc(str(sec["step"]))}</span>' if sec.get("step") else ""
    )
    reasoning = sec.get("reasoning_html", "") or ""
    evidence = sec.get("evidence_html", "") or ""
    sec_id = _slug(str(sec["id"]))
    return f'<div class="section" id="{sec_id}">{step}<h2>{_esc(str(sec["title"]))}</h2>{reasoning}{evidence}</div>'


def table(
    df: pd.DataFrame,
    *,
    scroll: bool = True,
    fmt: dict | None = None,
    cls: str = "t",
    html_fmt: bool = False,
) -> str:
    """Render a DataFrame as an HTML table, wrapped in ``.scroll-x`` by default.

    ``fmt`` maps column name -> a callable ``value -> str`` for cell formatting.
    Formatter output is **HTML-escaped by default** (``value -> str`` is plain
    text); set ``html_fmt=True`` only if your formatters intentionally return
    trusted HTML (e.g. gradient-colored cells).
    """
    fmt = fmt or {}
    cols = list(df.columns)
    head = "".join(f"<th>{_esc(str(c))}</th>" for c in cols)
    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if c in fmt:
                out = fmt[c](v)
                cells.append(f"<td>{out if html_fmt else _esc(str(out))}</td>")
            else:
                disp = (
                    ""
                    if (v is None or (isinstance(v, float) and pd.isna(v)))
                    else _esc(str(v))
                )
                cells.append(f"<td>{disp}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    safe_cls = _css_classes(cls, "t")
    html = f'<table class="{safe_cls}"><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'
    if scroll:
        return f'<div class="scroll-x">{html}</div>'
    return html


def plot(
    fig_or_traces, layout: dict | None = None, div_id: str = "plot", height: int = 340
) -> str:
    """A Plotly div + its ``Plotly.newPlot`` call, using the INLINED bundle (no CDN).

    ``fig_or_traces`` may be a list of trace dicts or a full figure dict
    (``{"data": [...], "layout": {...}}``). Returns a self-contained HTML fragment;
    the Plotly library itself is embedded once by :func:`page`.
    """
    if isinstance(fig_or_traces, dict) and "data" in fig_or_traces:
        traces = fig_or_traces["data"]
        layout = {**fig_or_traces.get("layout", {}), **(layout or {})}
    else:
        traces = fig_or_traces
        layout = layout or {}
    base_layout = {
        "font": {
            "family": "-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif",
            "size": 12,
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 52, "r": 18, "t": 28, "b": 38},
    }
    merged = {**base_layout, **layout}
    # div_id reaches an HTML attribute AND a JS string -> slug it so both agree
    # and neither can inject markup; dumps() keeps the JS string safe too.
    did = _slug(str(div_id))
    return (
        f'<div class="scroll-x"><div id="{did}" style="height:{int(height)}px;min-width:320px"></div></div>'
        f"<script>Plotly.newPlot({dumps(did)},{dumps(traces)},{dumps(merged)},"
        f"{{responsive:true,displayModeBar:false}});</script>"
    )


def kpi_row(items: list[dict]) -> str:
    """A KPI strip. Each item = ``{"v": value, "l": label, "c": ""|good|bad|warn}``.

    ``v``/``l`` are plain text (escaped); ``c`` is a tone class (allowlisted).
    """
    cells = "".join(
        f'<div class="kpi {_kind(it.get("c"))}"><div class="v">{_esc(it["v"])}</div>'
        f'<div class="l">{_esc(it["l"])}</div></div>'
        for it in items
    )
    return f'<div class="kpi-row">{cells}</div>'


def banner(title: str, body: str, *, kind: str = "") -> str:
    """A call-out banner. ``title`` is plain text (escaped); ``body`` is trusted
    HTML; ``kind`` is a tone class (``""|good|bad|warn``, allowlisted)."""
    k = _kind(kind)
    k = f" {k}" if k else ""
    head = f"<h4>{_esc(title)}</h4>" if title else ""
    return f'<div class="banner{k}">{head}{body}</div>'


def _esc(s: str) -> str:
    # escape the five characters that matter in text + double-quoted attributes,
    # so _esc is safe for both element text and attribute values.
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# allowlist of tone classes accepted on cards/KPIs/banners; anything else -> "".
_KINDS = {"", "good", "bad", "warn"}


def _kind(c) -> str:
    """Clamp a caller-supplied CSS tone class to the known-safe allowlist."""
    c = str(c or "").strip()
    return c if c in _KINDS else ""


import re as _re  # noqa: E402

_CSS_TOKEN = _re.compile(r"^-?[_a-zA-Z][-_a-zA-Z0-9]*$")


def _css_classes(value, default: str) -> str:
    """Keep only well-formed CSS identifier tokens from a class string.

    Prevents ``cls='t" onclick="..."'`` from breaking out of the ``class``
    attribute; anything that isn't a valid identifier token is dropped.
    """
    toks = [t for t in str(value or "").split() if _CSS_TOKEN.match(t)]
    return " ".join(toks) or default


# ---------------------------------------------------------------------------
# page assembly
# ---------------------------------------------------------------------------


def page(
    title: str,
    sections: list,
    *,
    favicon: str | None = None,
    subtitle: str | None = None,
    thesis: str | None = None,
    eyebrow: str | None = None,
    badges: list[str] | None = None,
    header_html: str | None = None,
    body_prefix_html: str = "",
    footer_html: str = "",
    extra_head: str = "",
    extra_script: str = "",
) -> str:
    """Assemble a full self-contained HTML doc.

    * inline CSS (:data:`SHARED_CSS` + ``extra_head``)
    * inline plotly (:func:`inline_plotly`) — never a CDN
    * a sticky nav built from the section titles

    ``sections`` is a list of dicts from :func:`section` (or raw HTML strings,
    which are emitted verbatim and skipped in the nav).
    """
    favicon_link = ""
    if favicon:
        # emoji favicon as an inline data-URI SVG (self-contained)
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
            "<text y='.9em' font-size='90'>" + _esc(favicon) + "</text></svg>"
        )
        import urllib.parse

        favicon_link = (
            f'<link rel="icon" href="data:image/svg+xml,{urllib.parse.quote(svg)}">'
        )

    nav_items = [s for s in sections if isinstance(s, dict)]
    nav_html = "".join(
        f'<a href="#{_slug(str(s["id"]))}">{_esc(s.get("nav_label") or s["title"])}</a>'
        for s in nav_items
    )

    if header_html is None:
        # eyebrow/subtitle/thesis/badges are plain-string API params -> escape.
        # (pass header_html for fully custom, trusted markup.)
        eb = f'<div class="eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
        sub = f'<p class="subtitle">{_esc(subtitle)}</p>' if subtitle else ""
        th = f'<p class="thesis">"{_esc(thesis)}"</p>' if thesis else ""
        badge_html = ""
        if badges:
            badge_html = (
                '<div class="badges">'
                + "".join(f'<span class="badge">{_esc(b)}</span>' for b in badges)
                + "</div>"
            )
        header_html = f'<div class="header"><div class="wrap">{eb}<h1>{_esc(title)}</h1>{th}{sub}{badge_html}</div></div>'

    body_sections = "".join(
        _section_html(s) if isinstance(s, dict) else str(s) for s in sections
    )
    footer = f'<div class="footer">{footer_html}</div>' if footer_html else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>{favicon_link}
{inline_plotly()}
<style>{SHARED_CSS}{extra_head}</style></head><body>
{header_html}
<div class="nav"><div class="wrap">{nav_html}</div></div>
{body_prefix_html}
<div class="container">
{body_sections}
</div>
{footer}
<script>{extra_script}</script>
</body></html>"""
