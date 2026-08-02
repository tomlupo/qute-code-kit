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

_EXTERNAL_REF = re.compile(r'<(?:script|link|img)[^>]*(?:src|href)="https?://[^"]+"')


def _has_external_refs(html: str) -> list[str]:
    return _EXTERNAL_REF.findall(html)


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
