"""Contract tests for the bundled reporting lib.

Guards the four properties the review flagged:
  1. drawdown is optional — derived from equity when absent (no JS crash path).
  2. embedded JSON is script-safe — ``</script>`` cannot break out of a block.
  3. section title/step/id are escaped/slugged — data cannot inject HTML.
  4. rendered reports are truly offline — zero external script/link/img refs.

Run (needs plotly/pandas in the venv):  pytest test_reporting.py -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # dir holding reporting/
from reporting import backtest_dashboard, base, research_story  # noqa: E402

# Catch every external-reference form, not just double-quoted http(s):
#   - a fetching tag (link/script/img/source/iframe/embed/object/video/audio/
#     track/input) with src/href/data/poster = http(s):// or protocol-relative //
#   - CSS url(...) and @import pointing off-box (incl. protocol-relative)
# Data URIs (data:) and in-page anchors stay allowed — those are self-contained.
_REMOTE = r"(?:https?:)?//"
_FETCH_TAG = r"link|script|img|source|iframe|embed|object|video|audio|track|input"
_EXTERNAL_REFS = [
    re.compile(
        rf"""<(?:{_FETCH_TAG})\b[^>]*?\b(?:src|href|data|poster)\s*=\s*["']?\s*{_REMOTE}""",
        re.I,
    ),
    re.compile(rf"""url\(\s*["']?\s*{_REMOTE}""", re.I),
    re.compile(rf"""@import\s+["']?\s*{_REMOTE}""", re.I),
]

# The vendored plotly.min.js is inlined verbatim and contains http(s) URLs as JS
# *string data* (help links etc.) — not DOM references. Strip only INLINE
# <script> bodies (those with no src attribute) before scanning, so we test the
# real markup without losing a genuinely external <script src=...>.
_INLINE_SCRIPT = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>.*?</script>", re.I | re.S
)


def _has_external_refs(html: str) -> list[str]:
    markup = _INLINE_SCRIPT.sub("<script></script>", html)
    hits: list[str] = []
    for pat in _EXTERNAL_REFS:
        hits += pat.findall(markup)
    return hits


# --- 2. script-safe JSON -----------------------------------------------------


def test_dumps_escapes_script_terminator():
    out = base.dumps({"x": "</script><img src=x onerror=alert(1)>"})
    assert "</script>" not in out
    assert "<\\/script>" in out


def test_dumps_escapes_line_separators():
    out = base.dumps({"x": "a\u2028b\u2029c"})
    assert "\u2028" not in out
    assert "\u2029" not in out
    assert "\\u2028" in out and "\\u2029" in out


def test_plot_payload_is_script_safe():
    frag = base.plot([{"x": [1], "y": [1], "name": "</script>"}], {}, "d")
    # the raw closing tag must not appear unescaped inside the emitted <script>
    assert 'name":"</script>' not in frag


# --- 3. escaped title / step / slugged id ------------------------------------


def test_section_title_and_step_escaped():
    html = base.page(
        "T", [base.section("<b>hi</b>", step="<i>1</i>", evidence_html="x")]
    )
    assert "<b>hi</b>" not in html
    assert "&lt;b&gt;hi&lt;/b&gt;" in html
    assert "&lt;i&gt;1&lt;/i&gt;" in html


def test_section_id_slugged_and_nav_matches():
    # a custom id with unsafe chars must be slugged consistently in anchor + nav href
    sec = base.section("Title", id='x" onload="alert(1)', evidence_html="e")
    html = base.page("T", [sec])
    assert 'onload="alert(1)"' not in html
    slug = base._slug('x" onload="alert(1)')
    assert f'id="{slug}"' in html
    assert f'href="#{slug}"' in html


def test_reasoning_and_evidence_html_stay_raw():
    # these ARE trusted raw HTML — must pass through unescaped
    html = base.page(
        "T",
        [base.section("S", reasoning_html="<em>keep</em>", evidence_html="<b>me</b>")],
    )
    assert "<em>keep</em>" in html
    assert "<b>me</b>" in html


# --- 1. optional drawdown ----------------------------------------------------


def test_backtest_render_without_drawdown():
    # a hand-built payload that omits drawdown must still render (JS derives it)
    payload = {
        "title": "no-dd",
        "profiles": {
            "P1": {
                "series": {
                    "s": {
                        "dates": ["2020-01-01", "2020-01-02"],
                        "equity": [1.0, 0.9],
                        "color": "#000",
                    }
                },
                "metrics": {"s": {"CAGR": 0.0}},
            }
        },
    }
    html = backtest_dashboard.render(payload)
    assert "ddOf(s)" in html  # fallback wired in
    assert "s.drawdown.map(" not in html  # no unconditional access
    assert not _has_external_refs(html)


def test_series_helpers_populate_drawdown():
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    r = pd.Series([0.01] * 5 + [-0.02] * 5, index=idx)
    s = backtest_dashboard.series_from_returns(r, color="#000")
    assert "drawdown" in s and len(s["drawdown"]) == len(s["equity"])


# --- 4. offline output -------------------------------------------------------


def test_backtest_dashboard_offline():
    idx = pd.date_range("2020-01-01", periods=30, freq="B")
    r = pd.Series([0.001] * 30, index=idx)
    payload = {
        "title": "t",
        "profiles": {
            "P1": {
                "series": {
                    "s": backtest_dashboard.series_from_returns(r, color="#000")
                },
                "metrics": {},
            }
        },
    }
    html = backtest_dashboard.render(payload)
    assert not _has_external_refs(html)
    assert "Plotly.newPlot" in html


def test_header_fields_escaped():
    html = base.page(
        "T",
        [base.section("S", evidence_html="x")],
        eyebrow="<script>e</script>",
        subtitle="<img src=x onerror=alert(1)>",
        thesis="</h1><b>t</b>",
        badges=["<i>b</i>"],
    )
    # tags only the payload could introduce must not appear un-escaped
    # (the page skeleton legitimately contains <h1>/<p>/<div>, so we check
    # payload-specific tokens: an injected <script>e, <img, and <i>b</i>).
    for tag in ("<script>e", "<img", "<i>b</i>", "onerror=alert(1)>"):
        assert tag not in html
    # and the escaped forms are present (proves the data went through _esc)
    assert "&lt;script&gt;e" in html and "&lt;img" in html and "&lt;i&gt;b" in html


def test_profile_ids_sanitized_and_consistent():
    idx = pd.date_range("2020-01-01", periods=20, freq="B")
    r = pd.Series([0.001] * 20, index=idx)
    bad = 'P1" onload="alert(1)'
    payload = {
        "title": "t",
        "profiles": {
            bad: {
                "series": {
                    "s": backtest_dashboard.series_from_returns(r, color="#000")
                },
                "metrics": {},
            }
        },
    }
    html = backtest_dashboard.render(payload)
    assert 'onload="alert(1)"' not in html  # raw key must not reach an attribute
    slug = base._slug(bad)
    assert f'id="eq_{slug}"' in html and f'id="dd_{slug}"' in html  # HTML anchors
    assert "'eq_'+dom" in html  # JS targets the same sanitized id via D.dom
    assert not _has_external_refs(html)


def test_profile_ids_deduped():
    # two distinct keys that slug to the same base must get unique DOM ids
    dom = backtest_dashboard._dom_ids({"A B": 1, "A_B": 1})
    assert len(set(dom.values())) == 2


def test_subsample_preserves_drawdown_trough():
    # equity rises to a high peak, dips (deep drawdown), recovers to a new low-ish
    # level whose absolute min != the drawdown trough
    import numpy as np

    idx = pd.date_range("2020-01-01", periods=400, freq="B")
    eq = pd.Series(
        np.linspace(1.0, 3.0, 200).tolist() + np.linspace(3.0, 1.5, 200).tolist(),
        index=idx,
    )
    trough = (eq / eq.cummax() - 1.0).idxmin()
    sub = backtest_dashboard._subsample(eq, 50)
    assert trough in sub.index


def test_plot_div_id_sanitized():
    frag = base.plot([{"x": [1], "y": [1]}], {}, 'p" onload="x')
    assert 'onload="x"' not in frag
    slug = base._slug('p" onload="x')
    assert f'id="{slug}"' in frag


def test_kpi_row_escapes_and_allowlists():
    html = base.kpi_row([{"v": "<b>1</b>", "l": "<i>x</i>", "c": "evil zzz"}])
    assert "<b>1</b>" not in html and "<i>x</i>" not in html
    assert 'class="kpi "' in html  # bad tone class clamped to ""


def test_kpi_row_keeps_valid_tone():
    assert 'class="kpi good"' in base.kpi_row([{"v": "1", "l": "x", "c": "good"}])


def test_banner_escapes_title_and_allowlists_kind():
    html = base.banner("<b>t</b>", "<em>body ok</em>", kind="evil")
    assert "<b>t</b>" not in html
    assert "<em>body ok</em>" in html  # body is trusted HTML
    assert 'class="banner"' in html  # kind clamped


def test_why_escapes_lead_allowlists_kind():
    html = research_story.why("<b>lead</b>", "<em>body</em>", kind="nope")
    assert "<b>lead</b>" not in html
    assert "<em>body</em>" in html
    assert 'class="why"' in html


def test_card_escapes_title_and_note_keeps_inner():
    html = research_story.card("<b>t</b>", "<em>inner</em>", note="<i>n</i>")
    assert "<b>t</b>" not in html and "<i>n</i>" not in html
    assert "<em>inner</em>" in html


def test_table_fmt_escaped_by_default():
    df = pd.DataFrame({"x": [1]})
    html = base.table(df, fmt={"x": lambda v: "<b>hi</b>"})
    assert "<b>hi</b>" not in html
    assert "&lt;b&gt;hi" in html


def test_table_html_fmt_opt_in():
    df = pd.DataFrame({"x": [1]})
    html = base.table(df, fmt={"x": lambda v: "<b>hi</b>"}, html_fmt=True)
    assert "<b>hi</b>" in html


def test_metric_label_escaped():
    import numpy as np

    idx = pd.date_range("2020-01-01", periods=20, freq="B")
    r = pd.Series([0.001] * 20, index=idx)
    payload = {
        "title": "t",
        "metrics_order": [("CAGR", "<b>lbl</b>", "pct", 2)],
        "profiles": {
            "P1": {
                "series": {
                    "s": backtest_dashboard.series_from_returns(r, color="#000")
                },
                "metrics": {"s": {"CAGR": 0.1}},
            }
        },
    }
    html = backtest_dashboard.render(payload)
    assert "<b>lbl</b>" not in html
    assert "&lt;b&gt;lbl" in html
    assert not np.isnan(0.0)  # keep numpy import used


def test_series_from_equity_drawdown_not_understated():
    import numpy as np

    # peak at t=200 is skipped by aggressive subsampling; full-series DD must
    # still reflect the deep dip from that peak.
    idx = pd.date_range("2020-01-01", periods=400, freq="B")
    eq = pd.Series(
        np.linspace(1.0, 3.0, 200).tolist() + np.linspace(3.0, 1.5, 200).tolist(),
        index=idx,
    )
    s = backtest_dashboard.series_from_equity(eq, color="#000", subsample_n=20)
    # trough drawdown is 1.5/3.0 - 1 = -0.5; must be present in the emitted dd
    assert min(v for v in s["drawdown"] if v is not None) <= -0.49


def test_table_cls_allowlisted():
    df = pd.DataFrame({"x": [1]})
    html = base.table(df, cls='t" onclick="alert(1)')
    assert 'onclick="alert(1)"' not in html
    assert 'class="t"' in html  # the injected junk token dropped, valid one kept


def test_profile_key_string_collision_rejected():
    idx = pd.date_range("2020-01-01", periods=5, freq="B")
    r = pd.Series([0.001] * 5, index=idx)
    s = backtest_dashboard.series_from_returns(r, color="#000")
    # 1 and "1" collide as JSON object keys — must be rejected, not silently dropped
    payload = {
        "title": "t",
        "profiles": {
            1: {"series": {"a": s}, "metrics": {}},
            "1": {"series": {"b": s}, "metrics": {}},
        },
    }
    try:
        backtest_dashboard.render(payload)
        raise AssertionError("expected ValueError on colliding profile keys")
    except ValueError:
        pass


def test_offline_check_catches_all_ref_forms():
    # the helper must flag single-quoted, unquoted, protocol-relative, and CSS refs
    assert _has_external_refs("<img src='http://x/a.png'>")
    assert _has_external_refs("<script src=//cdn.example/x.js></script>")
    assert _has_external_refs('<link href="https://cdn/x.css">')
    assert _has_external_refs("<style>a{background:url(//evil/x.png)}</style>")
    assert _has_external_refs("<style>@import '//evil/x.css';</style>")
    # but data URIs and in-page anchors are fine, and JS-string URLs are ignored
    assert not _has_external_refs('<img src="data:image/png;base64,AAAA">')
    assert not _has_external_refs('<a href="#section">x</a>')
    assert not _has_external_refs('<script>var u="https://api.example/x";</script>')


def test_research_story_offline():
    sec = [
        base.section(
            "S",
            reasoning_html=research_story.why("L", "b"),
            evidence_html=base.table(pd.DataFrame({"a": [1]})),
        )
    ]
    html = research_story.render(
        sec, title="s", thesis="t", kpis=[{"v": "1", "l": "x"}]
    )
    assert not _has_external_refs(html)
